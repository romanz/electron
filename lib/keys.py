# Copyright (c) 2017-2018, Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.


import lib.cashaddr as cashaddr
from lib.hash import hash160
from lib.util import to_bytes, hex_to_bytes, cachedproperty
from collections import namedtuple


class KeyError(Exception):
    pass


# A namedtuple for easy comparison and unique hashing
class Address(namedtuple("AddressTuple", "hash160 kind")):

    # Address kinds
    ADDR_P2PKH = 0
    ADDR_P2SH = 1

    def __new__(cls, hash160, kind):
        assert kind in (cls.ADDR_P2PKH, cls.ADDR_P2SH)
        hash160 = to_bytes(hash160)
        if len(hash160) != 20:
            raise AddressError('hash160 must be 20 bytes')
        return super().__new__(cls, hash160, kind)

    @classmethod
    def from_string(cls, string):
        '''Construct from an address string.'''
        raw = Base58.decode_check(string)

        # Require version byte(s) plus hash160.
        if len(raw) != 21:
            raise AddressError('invalid address: {}'.format(string))

        verbyte, hash160 = raw[0], raw[1:]
        if verbyte in [NetworkConstants.ADDRTYPE_P2PKH,
                       NetworkConstants.ADDRTYPE_P2PKH_BITPAY]:
            kind = cls.ADDR_P2PKH
        elif verbyte in [NetworkConstants.ADDRTYPE_P2SH,
                         NetworkConstants.ADDRTYPE_P2SH_BITPAY]:
            kind = cls.ADDR_P2SH
        else:
            raise AddressError('unknown version byte: {}'.format(verbyte))

        return cls(hash160, kind)

    @classmethod
    def is_valid(cls, string):
        try:
            cls.from_string(string)
            return True
        except Exception:
            return False

    @classmethod
    def from_P2PKH_hash(cls, hash160):
        '''Construct from a P2PKH hash160.'''
        return cls(hash160, cls.ADDR_P2PKH)

    @classmethod
    def from_P2SH_hash(cls, hash160):
        '''Construct from a P2PKH hash160.'''
        return cls(hash160, cls.ADDR_P2SH)

    @classmethod
    def from_multisig_script(cls, script):
        return cls.from_P2SH_hash(hash160(script))

    def to_string(self):
        '''Converts to a Base58 string.'''
        return Base58.encode_check(bytes([verbyte]) + self.hash160)

    def to_script(self):
        '''Return a binary script to pay to the address.'''
        if self.kind == self.ADDR_P2PKH:
            return Script.P2PKH_script(self.hash160)
        else:
            return Script.P2SH_script(self.hash160)

    def to_script_hex(self):
        '''Return a script to pay to the address as a hex string.'''
        return self.to_script().hex()

    def to_scripthash(self):
        '''Returns the hash of the script in binary.'''
        return sha256(self.to_script())

    def to_scripthash_hex(self):
        '''Like other bitcoin hashes this is reversed when written in hex.'''
        return hash_to_hex_str(self.to_scripthash())

    def __str__(self):
        return self.to_ui_string()

    def __repr__(self):
        return '<Address {}>'.format(self.__str__())


class BCHAddress(Address):

    # Address formats
    FMT_CASHADDR = 0
    FMT_LEGACY = 1
    FMT_BITPAY = 2   # Supported temporarily only for compatibility

    # At some stage switch to FMT_CASHADDR
    FMT_UI = FMT_LEGACY

    @classmethod
    def from_string(cls, string):
        '''Construct from an address string.'''
        if len(string) > 35:
            return cls.from_cashaddr_string(string)
        return super().from_string(string)

    @classmethod
    def show_cashaddr(cls, on):
        cls.FMT_UI = cls.FMT_CASHADDR if on else cls.FMT_LEGACY

    @classmethod
    def from_cashaddr_string(cls, string):
        '''Construct from a cashaddress string.'''
        prefix = NetworkConstants.CASHADDR_PREFIX
        if string.upper() == string:
            prefix = prefix.upper()
        if not string.startswith(prefix + ':'):
            string = ':'.join([prefix, string])
        addr_prefix, kind, addr_hash = cashaddr.decode(string)
        if addr_prefix != prefix:
            raise AddressError('address has unexpected prefix {}'
                               .format(addr_prefix))
        if kind == cashaddr.PUBKEY_TYPE:
            return cls(addr_hash, cls.ADDR_P2PKH)
        else:
            assert kind == cashaddr.SCRIPT_TYPE
            return cls(addr_hash, cls.ADDR_P2SH)

    def to_cashaddr(self):
        if self.kind == self.ADDR_P2PKH:
            kind  = cashaddr.PUBKEY_TYPE
        else:
            kind  = cashaddr.SCRIPT_TYPE
        return cashaddr.encode(NetworkConstants.CASHADDR_PREFIX, kind,
                               self.hash160)

    def to_string(self, fmt):
        '''Converts to a string of the given format.'''
        if fmt == self.FMT_CASHADDR:
            return self.to_cashaddr()

        if fmt == self.FMT_LEGACY:
            if self.kind == self.ADDR_P2PKH:
                verbyte = NetworkConstants.ADDRTYPE_P2PKH
            else:
                verbyte = NetworkConstants.ADDRTYPE_P2SH
        elif fmt == self.FMT_BITPAY:
            if self.kind == self.ADDR_P2PKH:
                verbyte = NetworkConstants.ADDRTYPE_P2PKH_BITPAY
            else:
                verbyte = NetworkConstants.ADDRTYPE_P2SH_BITPAY
        else:
            raise AddressError('unrecognised format')

    def to_full_string(self, fmt):
        '''Convert to text, with a URI prefix for cashaddr format.'''
        text = self.to_string(fmt)
        if fmt == self.FMT_CASHADDR:
            text = ':'.join([NetworkConstants.CASHADDR_PREFIX, text])
        return text

    def to_ui_string(self):
        '''Convert to text in the current UI format choice.'''
        return self.to_string(self.FMT_UI)

    def to_full_ui_string(self):
        '''Convert to text, with a URI prefix if cashaddr.'''
        return self.to_full_string(self.FMT_UI)

    def to_URI_components(self):
        '''Returns a (scheme, path) pair for building a URI.'''
        scheme = NetworkConstants.CASHADDR_PREFIX
        path = self.to_ui_string()
        # Convert to upper case if CashAddr
        if self.FMT_UI == self.FMT_CASHADDR:
            scheme = scheme.upper()
            path = path.upper()
        return scheme, path


class PublicKeyBase(object):

    @classmethod
    def _validate_bytes(cls, pubkey):
        '''Create from a public key expressed as binary bytes.'''
        pubkey = to_bytes(pubkey)
        if len(pubkey) == 33 and pubkey[0] in (2, 3):
            pass  # Compressed
        elif len(pubkey) == 65 and pubkey[0] == 4:
            pass
        else:
            raise KeyError(f'invalid public key {pubkey.hex()}')
        return pubkey

    def is_compressed(self):
        '''Returns True if the pubkey is compressed.'''
        return len(self.pubkey) == 33

    @cachedproperty
    def address(self):
        '''Convert to an Address object.'''
        return Address(hash160(self.pubkey), Address.ADDR_P2PKH)

    def to_P2PKH_script(self):
        '''Return a P2PKH script.'''
        return self.address.to_script()

    def to_script(self):
        '''Note this returns the P2PK script.'''
        return Script.P2PK_script(self.pubkey)

    def to_scripthash(self):
        '''Returns the hash of the script in binary.'''
        return sha256(self.to_script())

    def to_scripthash_hex(self):
        '''Like other bitcoin hashes this is reversed when written in hex.'''
        return hash_to_hex_str(self.to_scripthash())

    def to_ui_string(self):
        '''Convert to a hexadecimal string.'''
        return __str__(self)

    def __str__(self):
        return self.pubkey.hex()


class PublicKey(namedtuple("PublicKeyTuple", "pubkey")):
    '''A raw public key.'''

    @classmethod
    def from_bytes(cls, pubkey):
        return cls(cls._validate_bytes(pubkey))

    @classmethod
    def from_string(cls, string):
        '''Create from a hex string.'''
        return cls.from_bytes(hex_to_bytes(string))

    def __repr__(self):
        return f'<PublicKey {self}>'


class HDPublicKey(PublicKeyBase, namedtuple("HDPublicKeyTuple", "pubkey n")):
    '''BIP32 public key.  Embeds its child index.'''

    @classmethod
    def from_bytes(cls, pubkey, n):
        return cls(cls._validate_bytes(pubkey), n)

    def __repr__(self):
        return f'<HDPublicKey {self}/{self.n}>'
