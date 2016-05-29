import os
import re
import archives
from db import DATABASE

IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.png', '.gif', '.tiff', '.bmp']
PAGE_NUM_REGEX = re.compile(r'([0-9]+)([a-zA-Z])?\.')


def splitext(*args, **kwargs):
    try:
        return getattr(os.path, '_splitext')(*args, **kwargs)
    except AttributeError:
        return os.path.splitext(*args, **kwargs)


def basename(*args, **kwargs):
    try:
        return getattr(os.path, '_basename')(*args, **kwargs)
    except AttributeError:
        return os.path.basename(*args, **kwargs)


def data_object(archive, filename):
    try:
        img_data = archive.read(unicode(filename))
    except UnicodeDecodeError:
        img_data = archive.read(filename)
    ext = splitext(filename)[-1]
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.tiff': 'image/tiff',
        '.bmp': 'image/bmp'
    }.get(ext, '*/*')
    return DataObject(img_data, mime_type)


class State(object):
    READ = 0
    UNREAD = 1
    IN_PROGRESS = 2


def thumb_transcode(url, w=150, h=150):
    """use the PMS photo transcoder for thumbnails"""
    return '/photo/:/transcode?url={}&height={}&width={}&maxSize=1'.format(String.Quote(url), w, h)


def decorate_title(archive, user, state, title):
    if state == State.UNREAD:
        indicator = Prefs['unread_symbol']
    elif state == State.IN_PROGRESS:
        cur, total = DATABASE.get_page_state(user, archive)
        if cur <= 0 or total <= 0:
            indicator = Prefs['in_progress_symbol']
        else:
            indicator = '{} [{}/{}]'.format(Prefs['in_progress_symbol'], cur, total)
    elif state == State.READ:
        indicator = Prefs['read_symbol']
    else:
        return title
    return '{} {}'.format('' if indicator is None else indicator.strip(), title)


def decorate_directory(user, state, title):
    if state == State.UNREAD:
        indicator = Prefs['unread_symbol']
    elif state == State.IN_PROGRESS:
        indicator = Prefs['in_progress_symbol']
    elif state == State.READ:
        indicator = Prefs['read_symbol']
    else:
        return title
    return '{} {}'.format('' if indicator is None else indicator.strip(), title)


def filtered_listdir(directory):
    """Return a list of only directories and compatible format files in `directory`"""
    dirs, comics = [], []
    udir = directory.encode('utf-8')
    for x in sorted_nicely(os.listdir(udir)):
        if os.path.isdir(os.path.join(udir, x)):
            l = dirs if bool(Prefs['dirs_first']) else comics
            l.append((x, True))
        elif splitext(x)[-1] in archives.FORMATS:
            comics.append((x, False))
    return dirs + comics


def sorted_nicely(l):
    """sort file names as you would expect them to be sorted"""
    def alphanum_key(key):
        return [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', key.lower())]
    return sorted(l, key=alphanum_key)


def is_series(directory):
    """determine if a directory can be considered a series"""
    try:
        for x in os.listdir(directory):
            if splitext(x)[-1] in archives.FORMATS:
                return True
    except Exception as e:
        return False
    return False
