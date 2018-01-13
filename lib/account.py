# Copyright (c) 2018, Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.


import lib.bip32 as bip32
from lib.keys import HDPublicKey


class PubKeyList(object):

    def __init__(self):
        self.pubkeys = []

    def is_beyond_limit(self, pubkey):
        return False

    def generate_gap(self):
        pass


class HDPubKeyList(PubKeyList):

    def __init__(self, gap_limit):
        super().__init__()
        if not isinstance(gap_limit, int):
            raise TypeError('gap limit must be an integer')
        if gap_limit < 1:
            raise ValueError('gap limit must be at least 1')
        self.gap_limit = gap_limit

    def child(self, n):
        raise NotImplementedError

    def generate_key(self, n):
        self.pubkeys.append(self.child(n))

    def generate_gap(self, max_used):
        assert isinstance(max_used, int) and max_used >= -1
        start = self.pubkeys[-1].n + 1 if self.pubkeys else 0
        end = max_used + self.gap_limit + 1
        for n in range(start, end):
            print(f'Generating key index {n}')
            self.generate_key(n)

    def is_beyond_limit(self, pubkey, max_used):
        assert isinstance(pubkey, BIP32PublicKey)
        assert isinstance(max_used, int) and max_used >= -1
        return pubkey.n > max_used + self.gap_limit


class BIP32PubKeyList(HDPubKeyList):

    def __init__(self, master_pubkey, gap_limit):
        super().__init__(gap_limit)
        if not isinstance(master_pubkey, bip32.MasterPubKey):
            raise TypeError('pubkey must be a BeIP32 MasterPubKey')
        self.master_pubkey = master_pubkey

    def child(self, n):
        pubkey_bytes = self.master_pubkey.child_compressed_pubkey(n)
        return HDPublicKey.from_bytes(pubkey_bytes, n)


class Account(object):

    '''This object maintains the addresses of an account, their
    transaction history, and the UTXOs.

    This object subscribes to the account's addresses with a remote
    server, and refreshes its state as transactions come in.  For HD
    accounts, it handles new address generation according to a gap
    limit.
    '''

    def __init__(self, rec_keys, chg_keys):
        self.rec_keys = rec_keys
        self.chg_keys = chg_keys
        self.history = {}

    async def sync(self):
        for addr_list in (self.rec_addr_list, self.chg_addr_list):
            for addr in addr_list:
                self.subscribe(addr)

    def set_address_history(self, addr, hist):
        self.history[addr] = hist
        self.gap_check_event.set()

    async def sync_gap_limit(self):
        while True:
            await self.gap_check_event.wait()


class BIP32Account(Account):

    def __init__(self, master_pubkey, rec_gap_limit, chg_gap_limit):
        assert isinstance(master_pubkey, bip32.MasterPubKey)
        rec_keys = BIP32PubKeyList(master_pubkey.child(0), rec_gap_limit)
        chg_keys = BIP32PubKeyList(master_pubkey.child(1), chg_gap_limit)
        super().__init__(rec_keys, chg_keys)
