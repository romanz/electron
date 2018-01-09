# Copyright (c) 2017-2018, Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.


from lib.util import to_bytes, hex_to_bytes, cachedproperty


class KeyError(Exception):
    pass


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
