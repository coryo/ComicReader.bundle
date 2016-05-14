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


def get_session_identifier():
    """Return a string that can consistently identify the current user of the channel"""
    h = hashlib.sha1(Request.Headers.get('X-Plex-Token', 'none')).hexdigest()
    try:
        if h in Dict['usernames']:
            return Dict['usernames'][h]
        else:
            Dict['usernames'][h] = get_username(Request.Headers['X-Plex-Token'])
            Dict.Save()
            return Dict['usernames'][h]
    except Exception as e:
        Log.Error('get_session_identifier: {}'.format(e))
        return h


def thumb_transcode(url, w=150, h=150):
    """use the PMS photo transcoder for thumbnails"""
    return '/photo/:/transcode?url={}&height={}&width={}&maxSize=1'.format(String.Quote(url), w, h)


def get_username(token):
    """retrieve the username for the given access token from plex.tv"""
    access_tokens = XML.ElementFromURL(
        'https://plex.tv/servers/{}/access_tokens.xml?auth_token={}'.format(
            Core.get_server_attribute('machineIdentifier'), os.environ['PLEXTOKEN']),
        cacheTime=CACHE_1HOUR)
    for child in access_tokens.getchildren():
        if child.get('token') == token:
            username = child.get('username')
            return username if username else child.get('title')
    return token


def decorate_title(archive, user, state, title):
    if state == State.UNREAD:
        indicator = Prefs['unread_symbol']
    elif state == State.IN_PROGRESS:
        try:
            indicator = '{} [{}/{}]'.format(Prefs['in_progress_symbol'], *status(user, archive))
        except Exception:
            indicator = Prefs['in_progress_symbol']
    elif state == State.READ:
        indicator = Prefs['read_symbol']
    return '{} {}'.format('' if indicator is None else indicator.strip(), title)


def filtered_listdir(directory):
    """Return a list of only directories and compatible format files in `directory`"""
    dirs, comics = [], []
    for x in sorted_nicely(os.listdir(directory)):
        if os.path.isdir(os.path.join(directory, x)):
            l = dirs if bool(Prefs['dirs_first']) else comics
            l.append((x, True))
        elif os.path.splitext(x)[-1] in FORMATS:
            comics.append((x, False))
    return dirs + comics


def sorted_nicely(l):
    """sort file names as you would expect them to be sorted"""
    def alphanum_key(key):
        return [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', key.lower())]
    return sorted(l, key=alphanum_key)


def read(user, archive, fuzz=5):
    """Return the read state of archive for the session user"""
    try:
        cur, total = Dict['read_states'][user][unicode(archive)]
        return State.READ if abs(total - cur) < fuzz else State.IN_PROGRESS
    except (KeyError, AttributeError):
        return State.UNREAD


def status(user, archive):
    try:
        cur, total = Dict['read_states'][user][unicode(archive)]
        return (int(cur), int(total))
    except (KeyError, AttributeError):
        return (0, 0)
