# Copyright (c) 2017-2018, Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.

'''Logic for BIP32 Hierarchical Key Derviation.'''

import struct
from collections import namedtuple

import ecdsa
import ecdsa.ellipticcurve as EC
import ecdsa.numbertheory as NT

from lib.hash import Base58, hmac_sha512, hash160
from lib.keys import PublicKeyBase
from lib.util import cachedproperty, bytes_to_int, int_to_bytes


class DerivationError(Exception):
    '''Raised when an invalid derivation occurs.'''


class _KeyBase(object):
    '''A BIP32 Key, public or private.'''

    CURVE = ecdsa.SECP256k1

    def __init__(self, chain_code, n, depth, parent_fingerprint):
        if not isinstance(chain_code, (bytes, bytearray)):
            raise TypeError('chain code must be raw bytes')
        if len(chain_code) != 32:
            raise ValueError('invalid chain code')
        if not 0 <= n < 1 << 32:
            raise ValueError('invalid child number')
        if not 0 <= depth < 256:
            raise ValueError('invalid depth')
        if not isinstance(parent_fingerprint, (bytes, bytearray)):
            raise TypeError('parent has bad type')
        if len(parent_fingerprint) != 4:
            raise ValueError('parent fingerprint must be length 4')
        self.chain_code = chain_code
        self.n = n
        self.depth = depth
        self.parent_fingerprint = parent_fingerprint

    def _hmac_sha512(self, msg):
        '''Use SHA-512 to provide an HMAC, returned as a pair of 32-byte
        objects.
        '''
        hmac = hmac_sha512(self.chain_code, msg)
        return hmac[:32], hmac[32:]

    def _extended_key(self, ver_bytes, raw_serkey):
        '''Return the 78-byte extended key given prefix version bytes and
        serialized key bytes.
        '''
        if not isinstance(ver_bytes, (bytes, bytearray)):
            raise TypeError('ver_bytes must be raw bytes')
        if len(ver_bytes) != 4:
            raise ValueError('ver_bytes must have length 4')
        if not isinstance(raw_serkey, (bytes, bytearray)):
            raise TypeError('raw_serkey must be raw bytes')
        if len(raw_serkey) != 33:
            raise ValueError('raw_serkey must have length 33')

        return (ver_bytes + bytes([self.depth])
                + self.parent_fingerprint + struct.pack('>I', self.n)
                + self.chain_code + raw_serkey)

    def fingerprint(self):
        '''Return the key's fingerprint as 4 bytes.'''
        return self.identifier()[:4]

    def WIF(self, wif_byte, compressed=True):
        '''Return the private key encoded in Wallet Import Format.'''
        payload = bytearray([wif_byte]) + self.privkey_bytes
        if compressed:
            payload.append(0x01)
        return Base58.encode_check(payload)

    def extended_key_string(self, ver_bytes):
        '''Return an extended key as a base58 string.'''
        return Base58.encode_check(self.extended_key(ver_bytes))


class MasterPubKey(_KeyBase):
    '''A BIP32 public key.'''

    def __init__(self, pubkey, chain_code, n, depth, pfingerprint=bytes(4)):
        super().__init__(chain_code, n, depth, pfingerprint)
        if isinstance(pubkey, ecdsa.VerifyingKey):
            self.verifying_key = pubkey
        else:
            self.verifying_key = self._verifying_key_from_pubkey(pubkey)

    @classmethod
    def _verifying_key_from_pubkey(cls, pubkey):
        '''Converts a 33-byte compressed pubkey into an ecdsa.VerifyingKey
        object'''
        if not isinstance(pubkey, (bytes, bytearray)):
            raise TypeError('pubkey must be raw bytes')
        if len(pubkey) != 33:
            raise ValueError('pubkey must be 33 bytes')
        if pubkey[0] not in (2, 3):
            raise ValueError('invalid pubkey prefix byte')
        curve = cls.CURVE.curve

        is_odd = pubkey[0] == 3
        x = bytes_to_int(pubkey[1:])

        # p is the finite field order
        a, b, p = curve.a(), curve.b(), curve.p()
        y2 = pow(x, 3, p) + b
        assert a == 0  # Otherwise y2 += a * pow(x, 2, p)
        y = NT.square_root_mod_prime(y2 % p, p)
        if bool(y & 1) != is_odd:
            y = p - y
        point = EC.Point(curve, x, y)

        return ecdsa.VerifyingKey.from_public_point(point, curve=cls.CURVE)

    @classmethod
    def compressed_pubkey(cls, verifying_key):
        '''Return the compressed public key from a verifying key as 33 bytes.'''
        point = verifying_key.pubkey.point
        prefix = bytes([2 + (point.y() & 1)])
        padded_bytes = _exponent_to_bytes(point.x())
        return prefix + padded_bytes

    @cachedproperty
    def pubkey_bytes(self):
        '''Return the compressed public key as 33 bytes.'''
        return self.compressed_pubkey(self.verifying_key)

    def ec_point(self):
        return self.verifying_key.pubkey.point

    def child_verkey_R(self, n):
        if not 0 <= n < (1 << 31):
            raise ValueError('invalid BIP32 public key child number')

        msg = self.pubkey_bytes + struct.pack('>I', n)
        L, R = self._hmac_sha512(msg)

        curve = self.CURVE
        L = bytes_to_int(L)
        if L >= curve.order:
            raise DerivationError

        point = curve.generator * L + self.ec_point()
        if point == EC.INFINITY:
            raise DerivationError

        return ecdsa.VerifyingKey.from_public_point(point, curve=curve), R

    def child(self, n):
        '''Return the derived child extended pubkey at index N.'''
        verkey, R = self.child_verkey_R(n)
        return MasterPubKey(verkey, R, n, self.depth + 1, self.fingerprint())

    def child_compressed_pubkey(self, n):
        '''Return the derived child extended pubkey at index N.'''
        verkey, R = self.child_verkey_R(n)
        return self.compressed_pubkey(verkey)

    def address(self, ver_byte):
        "The public key as a P2PKH address"
        return Base58.encode_check(bytes([ver_byte])
                                   + hash160(self.pubkey_bytes))

    def identifier(self):
        '''Return the key's identifier as 20 bytes.'''
        return hash160(self.pubkey_bytes)

    def extended_key(self, ver_bytes):
        '''Return a raw extended public key.'''
        return self._extended_key(ver_bytes, self.pubkey_bytes)


class MasterPrivKey(_KeyBase):
    '''A BIP32 private key.'''

    HARDENED = 1 << 31

    def __init__(self, privkey, chain_code, n, depth, pfingerprint=bytes(4)):
        super().__init__(chain_code, n, depth, pfingerprint)
        if isinstance(privkey, ecdsa.SigningKey):
            self.signing_key = privkey
        else:
            self.signing_key = self._signing_key_from_privkey(privkey)

    @classmethod
    def _signing_key_from_privkey(cls, privkey):
        '''Converts a 32-byte privkey into an ecdsa.SigningKey object.'''
        exponent = cls._privkey_secret_exponent(privkey)
        return ecdsa.SigningKey.from_secret_exponent(exponent, curve=cls.CURVE)

    @classmethod
    def _privkey_secret_exponent(cls, privkey):
        '''Return the private key as a secret exponent if it is a valid private
        key.'''
        if not isinstance(privkey, (bytes, bytearray)):
            raise TypeError('privkey must be raw bytes')
        if len(privkey) != 32:
            raise ValueError('privkey must be 32 bytes')
        exponent = bytes_to_int(privkey)
        if not 1 <= exponent < cls.CURVE.order:
            raise ValueError('privkey represents an invalid exponent')

        return exponent

    @classmethod
    def from_seed(cls, seed):
        # This hard-coded message string seems to be coin-independent...
        hmac = hmac_sha512(b'Bitcoin seed', seed)
        privkey, chain_code = hmac[:32], hmac[32:]
        return cls(privkey, chain_code, 0, 0)

    @cachedproperty
    def privkey_bytes(self):
        '''Return the serialized private key (no leading zero byte).'''
        return _exponent_to_bytes(self.secret_exponent())

    @cachedproperty
    def public_key(self):
        '''Return the corresponding extended public key.'''
        verifying_key = self.signing_key.get_verifying_key()
        return MasterPubKey(verifying_key, self.chain_code, self.n, self.depth,
                            self.parent_fingerprint)

    def ec_point(self):
        return self.public_key.ec_point()

    def secret_exponent(self):
        '''Return the private key as a secret exponent.'''
        return self.signing_key.privkey.secret_multiplier

    def child(self, n):
        '''Return the derived child extended privkey at index N.'''
        if not 0 <= n < (1 << 32):
            raise ValueError('invalid BIP32 private key child number')

        if n >= self.HARDENED:
            serkey = b'\0' + self.privkey_bytes
        else:
            serkey = self.public_key.pubkey_bytes

        msg = serkey + struct.pack('>I', n)
        L, R = self._hmac_sha512(msg)

        curve = self.CURVE
        L = bytes_to_int(L)
        exponent = (L + bytes_to_int(self.privkey_bytes)) % curve.order
        if exponent == 0 or L >= curve.order:
            raise DerivationError

        privkey = _exponent_to_bytes(exponent)

        return MasterPrivKey(privkey, R, n, self.depth + 1, self.fingerprint())

    def address(self, coin):
        "The public key as a P2PKH address"
        return self.public_key.address(coin)

    def identifier(self):
        '''Return the key's identifier as 20 bytes.'''
        return self.public_key.identifier()

    def extended_key(self, ver_bytes):
        '''Return a raw extended private key.'''
        return self._extended_key(ver_bytes, b'\0' + self.privkey_bytes)


def _exponent_to_bytes(exponent):
    '''Convert an exponent to 32 big-endian bytes'''
    return (bytes(32) + int_to_bytes(exponent))[-32:]

def _from_extended_key(ekey):
    '''Return a MasterPubKey or MasterPrivKey from an extended key raw bytes.'''
    if not isinstance(ekey, (bytes, bytearray)):
        raise TypeError('extended key must be raw bytes')
    if len(ekey) != 78:
        raise ValueError('extended key must have length 78')

    depth = ekey[4]
    pfingerprint = ekey[5:9]
    n, = struct.unpack('>I', ekey[9:13])
    chain_code = ekey[13:45]

    if ekey[45]:
        # A public key - constructor asserts the initial byte is 2 or 3
        return MasterPubKey(ekey[45:], chain_code, n, depth, pfingerprint)
    else:
        return MasterPrivKey(ekey[46:], chain_code, n, depth, pfingerprint)


def from_extended_key_string(ekey_str):
    '''Given an extended key string, such as

    xpub6BsnM1W2Y7qLMiuhi7f7dbAwQZ5Cz5gYJCRzTNainXzQXYjFwtuQXHd
    3qfi3t3KJtHxshXezfjft93w4UE7BGMtKwhqEHae3ZA7d823DVrL

    return a (key, verbytes) pair.   key is either a MasterPubKey or
    MasterPrivKey.  verbytes is a bytes object of length 4.

    Caller might want to select coin based on the version bytes, and
    check public or private as appropriate.  Sadly version bytes are
    not unique across coins, so this has limited value.
    '''
    ekey = Base58.decode_check(ekey_str)
    key = _from_extended_key(ekey)
    return key, ekey[:4]
