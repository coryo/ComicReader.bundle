"""
Note: this is bad.
"""
import sys
import os
from subprocess import Popen, PIPE, STDOUT


SZ_TOOL = None


class SZipFile(object):

    def __init__(self, szfile):
        self.archive = os.path.abspath(szfile)
        self._list = None

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
            self._list = [x.split() for x in file_lines]
        return [x[-1] for x in self._list]

    def read(self, file):
        cmd = [SZ_TOOL, 'x', '-so', self.archive, file]
        p = custom_popen(cmd)
        return p.communicate()[0]


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
