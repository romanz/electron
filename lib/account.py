# Copyright (c) 2018, Neil Booth
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.

class AddressSource(object):

    pass


class HDSource(AddressSource):




class BIP32Source(HDSource):
    pass


class Address(object):
    pass


class AddressList(object):

    def __init__(self, source, gap_limit, addresses):
        if not all(isinstance(address, Address) for address in addresses):
            raise TypeError('each address must be an Address object')
        if not isinstance(gap_limit, int):
            raise TypeError('gap limit must be an integer')
        if gap_limit < 0:
            raise ValueError('gap limit cannot be negative')
        self.gap_limit = gap_limit
        self.addresses = addresses

    def generate_addresses(self, count):
        first = len(self.addresses)
        for index in range(first, first + count):
            self.addresses.append(self.source.


class Account(object):

    '''This object maintains the addresses of an account, their
    transaction history, and the UTXOs.

    This object subscribes to the account's addresses with a remote
    server, and refreshes its state as transactions come in.  For HD
    accounts, it handles new address generation according to a gap
    limit.
    '''

    def __init__(self, source, rec_addr_list, chg_addr_list):
        self.source = source
        self.rec_addr_list = rec_addr_list
        self.chg_addr_list = chg_addr_list
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
