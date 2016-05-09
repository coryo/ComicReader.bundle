# ComicReader.bundle by Cory Parsons <babylonstudio@gmail.com>
# https://github.com/coryo/ComicReader.bundle
# Supporting CBR, CBZ, CB7

import os
import json
import hashlib
import re
from io import open
from updater import Updater

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


def get_last_viewed_comic():
    with open(SharedCodeService.formats.DB_FILE, 'r') as f:
        db = json.loads(f.read())
        sid = get_session_identifier()
        Log.Info('Session id: {}'.format(sid))
        if sid in db:
            try:
                archive, filename = db[sid]
            except:
                archive, filename, fmt = db[sid]
            title = archive.split('/')[-1].split('\\')[-1]
            return PhotoAlbumObject(key=Callback(Comic, archive=archive, filename=filename),
                                    rating_key=hashlib.sha1(archive).hexdigest(),
                                    title=u'>> {}: {}'.format(sid, title),
                                    thumb=thumb_transcode(Callback(SharedCodeService.formats.get_cover,
                                                                   archive=archive)))


def filtered_listdir(directory):
    """Return a list of only directories and compatible format files in `directory`"""
    return [
        (x, os.path.isdir(os.path.join(directory, x))) for x in sorted_nicely(os.listdir(directory)) if
        os.path.isdir(os.path.join(directory, x)) or
        os.path.splitext(x)[-1] in SharedCodeService.formats.FORMATS
    ]


def sorted_nicely(l):
    def alphanum_key(key):
        return [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', key.lower())]
    return sorted(l, key=alphanum_key)


def Start():
    Route.Connect(PREFIX + '/getimage', SharedCodeService.formats.get_image)
    Route.Connect(PREFIX + '/getthumb', SharedCodeService.formats.get_thumb)
    Route.Connect(PREFIX + '/getcover', SharedCodeService.formats.get_cover)
    ObjectContainer.title1 = NAME
    if 'usernames' not in Dict:
        Dict['usernames'] = {}


@handler(PREFIX, NAME)
def MainMenu():
    SharedCodeService.formats.init_rar(Prefs['unrar'])
    SharedCodeService.formats.init_sz(Prefs['seven_zip'])

    oc = ObjectContainer(no_cache=True)
    if bool(Prefs['update']):
        Updater(PREFIX + '/updater', oc)

    if bool(Prefs['resume']) and os.path.isfile(SharedCodeService.formats.DB_FILE):
        try:
            oc.add(get_last_viewed_comic())
        except Exception as e:
            Log.Error('Unable to add resume comic: {}'.format(e))
    for x in BrowseDir(Prefs['cb_path'], page_size=int(Prefs['page_size'])).objects:
        oc.add(x)
    return oc


@route(PREFIX + '/browse', page_size=int, offset=int)
def BrowseDir(cur_dir, page_size=20, offset=0):
    oc = ObjectContainer(no_cache=True)
    try:
        dir_list = filtered_listdir(cur_dir)
        page = dir_list[offset:offset + page_size]
    except Exception as e:
        Log.Error(e)
        return error_message('bad path', 'bad path')
    for item, is_dir in page:
        full_path = os.path.join(cur_dir, item)
        oc.add(
            DirectoryObject(key=Callback(BrowseDir, cur_dir=full_path, page_size=page_size),
                            title=item) if is_dir else
            PhotoAlbumObject(key=Callback(Comic, archive=full_path),
                             rating_key=hashlib.md5(full_path).hexdigest(),
                             title=unicode(os.path.splitext(item)[0]),
                             thumb=thumb_transcode(Callback(SharedCodeService.formats.get_cover,
                                                            archive=full_path)))
        )
    if offset + page_size < len(dir_list):
        oc.add(NextPageObject(key=Callback(BrowseDir, cur_dir=cur_dir,
                              page_size=page_size, offset=offset + page_size)))
    return oc


@route(PREFIX + '/comic')
def Comic(archive, filename=None):
    oc = ObjectContainer(title2=unicode(archive), no_cache=True)
    try:
        a = SharedCodeService.formats.get_archive(archive)
    except SharedCodeService.formats.ArchiveError as e:
        Log.Error(e)
        return error_message('bad archive', 'unable to open archive: {}'.format(archive))
    files = a.namelist()
    if filename is not None:
        pos = files.index(filename)
        files = files[max(0, pos - 3):]
    for f in sorted_nicely(files):
        if f.endswith('/'):
            continue
        page = f.split('/')[-1] if '/' in f else f
        oc.add(PhotoObject(url=SharedCodeService.formats.build_url(archive, f, get_session_identifier()),
                           title=unicode(page) if f != filename else '>> {}'.format(page),
                           thumb=thumb_transcode(Callback(SharedCodeService.formats.get_thumb,
                                                          archive=archive,
                                                          filename=f))))
    return oc
