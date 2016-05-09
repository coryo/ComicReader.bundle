# szipfile.py
#
# Copyright (c) 2016  Cory Parsons <babylonstudio@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
This is a Python module for 7z archive reading.  The interface
is made as :mod:`zipfile`-like as possible.
"""

import sys
import os
from subprocess import Popen, PIPE
from binascii import unhexlify
import re

SIGNATURE = unhexlify('377abcaf271c')
SZ_TOOL = '7z'
SZ_L = re.compile(r'([\d-]+)\s+([\d:]+)\s+([A-Z.]{5})\s+(\d+)?\s+(\d+)?\s+([^\r\n]*)')


class SZExecutableError(Exception):
    pass


class NotSZFile(Exception):
    pass


class SZipFile(object):

    def __init__(self, szfile):
        self.archive = os.path.abspath(szfile)
        self._list = None

        with open(self.archive, 'rb') as f:
            ksig = f.read(len(SIGNATURE))
            if ksig != SIGNATURE:
                raise NotSZFile('{} is not a 7z file.'.format(self.archive))

    def namelist(self):
        """ Return a list of all the file names in the archive """
        if self._list is None:
            self._get_file_list()
        return [x.name for x in self._list]

    def read(self, file):
        """ Return data of file with `7z x -so archive.7z file` """
        cmd = [SZ_TOOL, 'x', '-so', self.archive, file]
        p = custom_popen(cmd)
        return p.communicate()[0]

    def _get_file_list(self):
        """ get files from `7z l` """
        p = custom_popen([SZ_TOOL, 'l', self.archive])
        out = p.communicate()[0]
        m = re.findall(SZ_L, out)
        self._list = [FileInfo(*x) for x in m if len(x) == 6]


def custom_popen(cmd):
    try:
        p = Popen(cmd, bufsize=0, stdout=PIPE, stdin=PIPE, stderr=None)
    except OSError as e:
        raise SZExecutableError('cant execute: {}'.format(cmd))
    return p


class FileInfo(object):
    __slots__ = (
        'date',
        'time',
        'attr',
        'size',
        'compressed',
        'name'
    )

    def __init__(self, date, time, attr, size, compressed, name):
        self.date = date
        self.time = time
        self.attr = attr
        self.size = size
        self.compressed = compressed
        self.name = name.replace('\\', '/')
        if self.attr[0] == 'D':
            self.name += '/'
