"""
Note: this is bad.
"""
import sys
import os
from subprocess import Popen, PIPE, STDOUT
import re


SZ_TOOL = None


class SZExecutableError(Exception):
    pass


class SZBadArchive(Exception):
    pass


class SZipFile(object):

    def __init__(self, szfile):
        self.archive = os.path.abspath(szfile)
        self._list = None
        if SZ_TOOL is None:
            raise SZExecutableError('7z executable has not been set')
        self.test()

    def namelist(self):
        if self._list is None:
            p = custom_popen([SZ_TOOL, 'l', self.archive])
            file_lines = []
            lines = p.communicate()[0].splitlines()
            for i, line in enumerate(lines):
                if line.startswith('----'):
                    x = 1
                    while not lines[i + x].startswith('-'):
                        file_lines.append(lines[i + x])
                        x += 1
                    break
            self._list = file_lines
        # Attr, Name  = x[20:25], x[53:]
        return [x[53:] + ('/' if x[20:25].endswith('D....') else '') for x in self._list]

    def read(self, file):
        cmd = [SZ_TOOL, 'x', '-so', self.archive, file.replace('\\', '/')]
        p = custom_popen(cmd)
        return p.communicate()[0]

    def test(self):
        cmd = [SZ_TOOL, 't', self.archive]
        p = custom_popen(cmd)
        r = p.communicate()[0]
        m = re.search(r'Everything is Ok', r, re.I)
        if not m:
            raise SZBadArchive('7zip: bad archive')



def custom_popen(cmd):
    """Disconnect cmd from parent fds, read only from stdout."""

    # # needed for py2exe
    creationflags = 0
    if sys.platform == 'win32':
        creationflags = 0x08000000 # CREATE_NO_WINDOW

    # run command
    try:
        p = Popen(cmd, bufsize=0, stdout=PIPE, stdin=PIPE, stderr=None, creationflags=creationflags)
    except OSError as e:
        raise e
    return p
