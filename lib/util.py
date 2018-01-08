# Copyright (c) 2016-2017, Neil Booth
#
# All rights reserved.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# and warranty status of this software.

'''Miscellaneous utility classes and functions.'''


import array
import inspect
from ipaddress import ip_address
import logging
import re
import sys
from collections import Container, Mapping
from struct import pack, Struct


class LoggedClass(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.log_prefix = ''
        self.throttled = 0

    def log_info(self, msg, throttle=False):
        # Prevent annoying log messages by throttling them if there
        # are too many in a short period
        if throttle:
            self.throttled += 1
            if self.throttled > 3:
                return
            if self.throttled == 3:
                msg += ' (throttling later logs)'
        self.logger.info(self.log_prefix + msg)

    def log_warning(self, msg):
        self.logger.warning(self.log_prefix + msg)

    def log_error(self, msg):
        self.logger.error(self.log_prefix + msg)


# Method decorator.  To be used for calculations that will always
# deliver the same result.  The method cannot take any arguments
# and should be accessed as an attribute.
class cachedproperty(object):

    def __init__(self, f):
        self.f = f

    def __get__(self, obj, type):
        obj = obj or type
        value = self.f(obj)
        setattr(obj, self.f.__name__, value)
        return value


def subclasses(base_class, strict=True):
    '''Return a list of subclasses of base_class in its module.'''
    def select(obj):
        return (inspect.isclass(obj) and issubclass(obj, base_class) and
                (not strict or obj != base_class))

    pairs = inspect.getmembers(sys.modules[base_class.__module__], select)
    return [pair[1] for pair in pairs]


def chunks(items, size):
    '''Break up items, an iterable, into chunks of length size.'''
    for i in range(0, len(items), size):
        yield items[i: i + size]


def bytes_to_int(be_bytes):
    '''Interprets a big-endian sequence of bytes as an integer'''
    return int.from_bytes(be_bytes, 'big')


def int_to_bytes(value):
    '''Converts an integer to a big-endian sequence of bytes'''
    return value.to_bytes((value.bit_length() + 7) // 8, 'big')


def int_to_varint(value):
    '''Converts an integer to a Bitcoin-like varint bytes'''
    if value < 0:
        raise ValueError("attempt to write size < 0")
    elif value < 253:
        return pack('<B', value)
    elif value < 2**16:
        return b'\xfd' + pack('<H', value)
    elif value < 2**32:
        return b'\xfe' + pack('<I', value)
    elif value < 2**64:
        return b'\xff' + pack('<Q', value)


unpack_int32_from = Struct('<i').unpack_from
unpack_int64_from = Struct('<q').unpack_from
unpack_uint16_from = Struct('<H').unpack_from
unpack_uint32_from = Struct('<I').unpack_from
unpack_uint64_from = Struct('<Q').unpack_from

hex_to_bytes = bytes.fromhex
