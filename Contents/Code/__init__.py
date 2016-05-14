# ComicReader.bundle by Cory Parsons <babylonstudio@gmail.com>
# https://github.com/coryo/ComicReader.bundle
# Supporting CBR, CBZ, CB7

import os
import hashlib
import random
import re
import time
from io import open

from updater import Updater
import formats

NAME = 'ComicReader'
PREFIX = '/photos/comicreader'


def error_message(error, message):
    Log.Error("ComicReader: {} - {}".format(error, message))
    return MessageContainer(header=unicode(error), message=unicode(message))


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

    user = formats.get_session_identifier()
    Log.Info('USER: {}'.format(user))

    if user not in Dict['read_states']:
        Dict['read_states'][user] = {}

    oc = ObjectContainer(no_cache=True)
    if bool(Prefs['update']):
        Updater(PREFIX + '/updater', oc)

    for x in BrowseDir(Prefs['cb_path'], page_size=int(Prefs['page_size']), user=user).objects:
        oc.add(x)
    return oc


@route(PREFIX + '/browse', page_size=int, offset=int)
def BrowseDir(cur_dir, page_size=20, offset=0, user=None):
    """Browse directories, with paging. Show directories and compatible archives."""
    oc = ObjectContainer(no_cache=True)
    try:
        dir_list = formats.filtered_listdir(cur_dir)
        page = dir_list[offset:offset + page_size]
    except Exception as e:
        Log.Error(e)
        return error_message('bad path', 'bad path')
    for item, is_dir in page:
        full_path = os.path.join(cur_dir, item)
        if is_dir:
            oc.add(DirectoryObject(
                key=Callback(BrowseDir, cur_dir=full_path, page_size=page_size, user=user),
                title=unicode(item),
                thumb=R('folder.png')))
        else:
            state = formats.read(user, full_path)
            title = os.path.splitext(item)[0]
            oc.add(DirectoryObject(
                key=Callback(ComicMenu, archive=full_path, title=title, user=user),
                title=unicode(formats.decorate_title(full_path, user, state, title)),
                thumb=formats.thumb_transcode(Callback(formats.get_cover, archive=full_path))))

    if offset + page_size < len(dir_list):
        oc.add(NextPageObject(key=Callback(BrowseDir, cur_dir=cur_dir,
                              page_size=page_size, offset=offset + page_size, user=user)))
    return oc


@route(PREFIX + '/comic/menu')
def ComicMenu(archive, title, user=None):
    """The 'main menu' for a comic. this allows for different functions to be added."""
    oc = ObjectContainer(title2=unicode(archive), no_cache=True)
    state = formats.read(user, archive)
    # Full comic
    oc.add(PhotoAlbumObject(
        key=Callback(Comic, archive=archive, user=user),
        rating_key=hashlib.md5(archive).hexdigest(),
        title=unicode(formats.decorate_title(archive, user, state, title)),
        thumb=formats.thumb_transcode(Callback(formats.get_cover,
                                               archive=archive))))
    # Resume
    if state == formats.State.IN_PROGRESS:
        cur, total = formats.status(user, archive)
        oc.add(DirectoryObject(title=unicode(L('resume')), thumb=R('resume.png'),
                               key=Callback(Comic, archive=archive, user=user, page=cur)))
    # Read/Unread toggle
    if state == formats.State.UNREAD or state == formats.State.IN_PROGRESS:
        oc.add(DirectoryObject(title=unicode(L('mark_read')), thumb=R('mark-read.png'),
                               key=Callback(MarkRead, user=user, archive=archive)))
    else:
        oc.add(DirectoryObject(title=unicode(L('mark_unread')), thumb=R('mark-unread.png'),
                               key=Callback(MarkUnread, user=user, archive=archive)))
    return oc


@route(PREFIX + '/comic', page=int)
def Comic(archive, user=None, page=0):
    """Return an oc with all pages in archive. if page > 0 return pages [page - Prefs['resume_length']:]"""
    oc = ObjectContainer(title2=unicode(archive), no_cache=True)
    try:
        a = formats.get_archive(archive)
    except formats.ArchiveError as e:
        Log.Error(e)
        return error_message('bad archive', 'unable to open archive: {}'.format(archive))
    for f in formats.sorted_nicely(a.namelist()):
        if f.endswith('/'):  # we're flattening the archive structure, so don't list the dirs.
            continue
        decoration = None
        if page > 0:
            m = re.search(r'([0-9]+)([a-zA-Z])?\.', f)
            if m:
                page_num = int(m.group(1))
                if page_num < page - int(Prefs['resume_length']):
                    continue
                if page_num <= page:
                    decoration = '>'
        page_title, ext = os.path.splitext(f)
        page_title, ext = os.path.basename(page_title), ext[1:]
        if decoration is not None:
            page_title = '{} {}'.format(decoration, page_title)

        oc.add(CreatePhotoObject(
            media_key=Callback(GetImage, archive=String.Encode(archive),
                               filename=String.Encode(f), user=user, extension=ext,
                               time=int(time.time()) if bool(Prefs['prevent_caching']) else 0),
            rating_key=hashlib.sha1('{}{}{}'.format(archive, f, user)).hexdigest(),
            title=unicode(page_title),
            thumb=formats.thumb_transcode(Callback(formats.get_thumb, archive=archive,
                                                   filename=f))))
    return oc


@route(PREFIX + '/markread')
def MarkRead(user, archive):
    Log.Info('Mark read. {} a={}'.format(user, archive))
    try:
        Dict['read_states'][user][unicode(archive)] = (0, 0)
        Dict.Save()
    except KeyError:
        Log.Error('could not mark read.')
    return error_message('marked', 'marked')


@route(PREFIX + '/markunread')
def MarkUnread(user, archive):
    Log.Info('Mark unread. a={}'.format(archive))
    try:
        del Dict['read_states'][user][unicode(archive)]
        Dict.Save()
    except Exception:
        Log.Error('could not mark unread.')
    return error_message('marked', 'marked')


@route(PREFIX + '/createphotoobject')
def CreatePhotoObject(rating_key, title, thumb, media_key=None):
    """simulate a url service"""
    po = PhotoObject(
        key=Callback(CreatePhotoObject, rating_key=rating_key, title=title, thumb=thumb),
        rating_key=rating_key, title=title, thumb=thumb)
    if media_key:
        po.add(MediaObject(parts=[PartObject(key=media_key)]))
    return po


@route(PREFIX + '/image/{user}/{archive}/{filename}.{extension}', time=int)
def GetImage(archive, filename, user, extension, time=0):
    """direct response with image data. setting a new time value should prevent
    clients from loading their cached copy so our page tracking code can run."""
    return formats.get_image(String.Decode(archive), String.Decode(filename), user)
