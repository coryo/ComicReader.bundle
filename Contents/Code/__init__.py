# ComicReader.bundle by Cory Parsons <babylonstudio@gmail.com>
# https://github.com/coryo/ComicReader.bundle
# Supporting CBR, CBZ, CB7

import os
import hashlib
import random
import re
from io import open

from updater import Updater
import formats

NAME = 'ComicReader'
PREFIX = '/photos/comicreader'


def error_message(error, message):
    Log.Error("ComicReader: {} - {}".format(error, message))
    return MessageContainer(header=unicode(error), message=unicode(message))


def get_session_identifier():
    """Return a string that can consistently identify the current user of the channel"""
    try:
        h = hashlib.sha1(Request.Headers['X-Plex-Token']).hexdigest()
        if h in Dict['usernames']:
            return Dict['usernames'][h]
        else:
            Dict['usernames'][h] = get_username(Request.Headers['X-Plex-Token'])
            Dict.Save()
            return Dict['usernames'][h]
    except Exception as e:
        Log.Error(e)
        return Request.Headers.get('X-Plex-Token', 'none')


def thumb_transcode(url, w=150, h=150):
    """ use the PMS photo transcoder for thumbnails """
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


def filtered_listdir(directory):
    """Return a list of only directories and compatible format files in `directory`"""
    dirs, comics = [], []
    for x in sorted_nicely(os.listdir(directory)):
        if os.path.isdir(os.path.join(directory, x)):
            if bool(Prefs['dirs_first']):
                dirs.append((x, True))
            else:
                comics.append((x, True))
        elif os.path.splitext(x)[-1] in formats.FORMATS:
            comics.append((x, False))
    return dirs + comics


def sorted_nicely(l):
    """sort file names as you would expect them to be sorted"""
    def alphanum_key(key):
        return [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', key.lower())]
    return sorted(l, key=alphanum_key)


def read(user, archive):
    """Return the read state of archive for the session user"""
    try:
        cur, total = Dict['read_states'][user][archive]
        return formats.State.READ if abs(total - cur) < 5 else formats.State.IN_PROGRESS
    except (KeyError, AttributeError):
        return formats.State.UNREAD


@route(PREFIX + '/markread')
def MarkRead(user, archive):
    Log.Info('Mark read. {} a={}'.format(user, archive))
    try:
        Dict['read_states'][user][archive] = (0, 0)
        Dict.Save()
    except KeyError:
        Log.Error('could not mark read.')
    return error_message('marked', 'marked')


@route(PREFIX + '/markunread')
def MarkUnread(user, archive):
    Log.Info('Mark unread. a={}'.format(archive))
    try:
        del Dict['read_states'][user][archive]
        Dict.Save()
    except Exception:
        Log.Error('could not mark unread.')
    return error_message('marked', 'marked')


###############################################################################


def Start():
    Route.Connect(PREFIX + '/getimage', formats.get_image)
    Route.Connect(PREFIX + '/getthumb', formats.get_thumb)
    Route.Connect(PREFIX + '/getcover', formats.get_cover)
    ObjectContainer.title1 = NAME

    if 'usernames' not in Dict:
        Dict['usernames'] = {}

    if 'read_states' not in Dict:
        Dict['read_states'] = {}

    if 'resume_states' not in Dict:
        Dict['resume_states'] = {}


@handler(PREFIX, NAME)
def MainMenu():
    formats.init_rar(Prefs['unrar'])
    formats.init_sz(Prefs['seven_zip'])

    user = get_session_identifier()
    if user not in Dict['read_states']:
        Dict['read_states'][user] = {}

    oc = ObjectContainer(no_cache=True)
    if bool(Prefs['update']):
        Updater(PREFIX + '/updater', oc)

    for x in BrowseDir(Prefs['cb_path'], page_size=int(Prefs['page_size']), user=user).objects:
        oc.add(x)
    return oc


def decorate_title(archive, user, state, title):
    if state == formats.State.UNREAD:
        indicator = Prefs['unread_symbol']
    elif state == formats.State.IN_PROGRESS:
        try:
            indicator = '{} [{}/{}]'.format(Prefs['in_progress_symbol'], *Dict['read_states'][user][archive])
        except Exception:
            indicator = Prefs['in_progress_symbol']
    elif state == formats.State.READ:
        indicator = Prefs['read_symbol']
    return u'{} {}'.format('' if indicator is None else indicator.strip(), title)


@route(PREFIX + '/browse', page_size=int, offset=int)
def BrowseDir(cur_dir, page_size=20, offset=0, user=None):
    oc = ObjectContainer(no_cache=True)
    try:
        dir_list = filtered_listdir(cur_dir)
        page = dir_list[offset:offset + page_size]
    except Exception as e:
        Log.Error(e)
        return error_message('bad path', 'bad path')
    for item, is_dir in page:
        full_path = os.path.join(cur_dir, item)
        if is_dir:
            oc.add(DirectoryObject(
                key=Callback(BrowseDir, cur_dir=full_path, page_size=page_size, user=user),
                title=item,
                thumb=R('folder.png')))
        else:
            state = read(user, full_path)
            title = unicode(os.path.splitext(item)[0])

            oc.add(DirectoryObject(
                key=Callback(ComicMenu, archive=full_path, title=title, user=user),
                title=decorate_title(full_path, user, state, title),
                thumb=thumb_transcode(Callback(formats.get_cover, archive=full_path))))

    if offset + page_size < len(dir_list):
        oc.add(NextPageObject(key=Callback(BrowseDir, cur_dir=cur_dir,
                              page_size=page_size, offset=offset + page_size, user=user)))
    return oc


@route(PREFIX + '/comic/menu')
def ComicMenu(archive, title, user=None):
    oc = ObjectContainer(title2=unicode(archive), no_cache=True)
    state = read(user, archive)

    oc.add(PhotoAlbumObject(
        key=Callback(Comic, archive=archive, user=user),
        rating_key=hashlib.md5(archive).hexdigest(),
        title=decorate_title(archive, user, state, title),
        thumb=thumb_transcode(Callback(formats.get_cover,
                                       archive=archive))))

    if state == formats.State.UNREAD or state == formats.State.IN_PROGRESS:
        oc.add(DirectoryObject(title=L('mark_read'), thumb=R('mark-read.png'),
                               key=Callback(MarkRead, user=user, archive=archive)))
    else:
        oc.add(DirectoryObject(title=L('mark_unread'), thumb=R('mark-unread.png'),
                               key=Callback(MarkUnread, user=user, archive=archive)))
    return oc


@route(PREFIX + '/comic')
def Comic(archive, user=None):
    oc = ObjectContainer(title2=unicode(archive), no_cache=True)
    try:
        a = formats.get_archive(archive)
    except formats.ArchiveError as e:
        Log.Error(e)
        return error_message('bad archive', 'unable to open archive: {}'.format(archive))
    files = a.namelist()

    for f in sorted_nicely(files):
        if f.endswith('/'):
            continue
        page = f.split('/')[-1] if '/' in f else f
        ext = f.split('.')[-1]
        rating_key = hashlib.sha1('{}{}{}'.format(archive, f, user)).hexdigest()
        cb = Callback(GetImage, archive=String.Encode(archive), filename=String.Encode(f), user=user, extension=ext)
        po = PhotoObject(key=Callback(MetadataObject, key=cb, rating_key=rating_key),
                         rating_key=rating_key,
                         title=unicode(page),
                         thumb=thumb_transcode(Callback(formats.get_thumb,
                                                        archive=archive,
                                                        filename=f)))
        po.add(MediaObject(parts=[PartObject(key=cb)]))
        oc.add(po)
    return oc


@route(PREFIX + '/metadata')
def MetadataObject(key, rating_key):
    return PhotoObject(key=key, rating_key=rating_key, title='x', summary='x')


@route(PREFIX + '/image/{user}/{archive}/{filename}.{extension}')
def GetImage(archive, filename, user, extension):
    return formats.get_image(String.Decode(archive), String.Decode(filename), user)
