import os
import re

import rarfile
import zipfile
import szipfile

FORMATS = ['.cbr', '.cbz', '.cb7', '.zip', '.rar', '.7z']
SUPPORT_PATH = os.path.join(Core.bundle_path.split('Plug-ins')[0], 'Plug-in Support', 'Data', Plugin.Identifier)


def init_rar(path):
    """Set the unrar executable"""
    if path:
        rarfile.UNRAR_TOOL = os.path.abspath(path)
    Log.Info('USING UNRAR EXECUTABLE: {}'.format(rarfile.UNRAR_TOOL))


def init_sz(path):
    """Set the 7z executable"""
    if path:
        szipfile.SZ_TOOL = os.path.abspath(path)
    Log.Info('USING 7ZIP EXECUTABLE: {}'.format(szipfile.SZ_TOOL))


def mime_type(filename):
    ext = os.path.splitext(filename)[-1]
    return {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.tiff': 'image/tiff',
        '.bmp': 'image/bmp'
    }.get(ext, '*/*')


class State(object):
    READ = 0
    UNREAD = 1
    IN_PROGRESS = 2


class ArchiveError(Exception):
    pass


def get_archive(archive):
    """Return an archive object.
    Some archives are given the wrong extension, so try opening it until it works."""
    try:
        return rarfile.RarFile(archive)
    except Exception:
        pass
    try:
        return zipfile.ZipFile(archive)
    except Exception:
        pass
    try:
        return szipfile.SZipFile(archive)
    except Exception:
        pass

    raise ArchiveError


def get_image(archive, filename, user):
    """Return the contents of `filename` from within `archive`. also do some other stuff."""
    a = get_archive(archive)

    # Get Page Numbers
    try:
        page_count = len(a.namelist())
        m = re.search(r'([0-9]+)([a-zA-Z])?\.', filename)
        cur_page = int(m.group(1)) if m else 0
        Log.Info('page_count {}/{}'.format(cur_page, page_count))
    except Exception:
        Log.Error('get_image: unable to get page numbers')
    # Write the Dict (read state)
    try:
        Dict['read_states'][user][unicode(archive)] = (cur_page, page_count)
    except Exception:
        Log.Error('unable to write dict')
    Dict.Save()
    return DataObject(a.read(filename), mime_type(filename))


def get_thumb(archive, filename):
    """Return the contents of `filename` from within `archive`."""
    try:
        a = get_archive(archive)
    except ArchiveError as e:
        Log.Error(str(e))
    else:
        return DataObject(a.read(filename), mime_type(filename))


def get_cover(archive):
    """Return the contents of the first file in `archive`."""
    try:
        a = get_archive(archive)
    except ArchiveError as e:
        Log.Error(str(e))
    else:
        x = sorted([x for x in a.namelist() if not x.endswith('/')])
        if x:
            return DataObject(a.read(x[0]), mime_type(x[0]))
