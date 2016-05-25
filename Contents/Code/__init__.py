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
import utils
import archives
from db import DATABASE

NAME = 'ComicReader'
PREFIX = '/photos/comicreader'


def error_message(error, message):
    Log.Error("ComicReader: {} - {}".format(error, message))
    return MessageContainer(header=unicode(error), message=unicode(message))


@route(PREFIX + '/getimage', archive=unicode)
def get_image(archive, filename, user):
    """Return the contents of `filename` from within `archive`. also do some other stuff."""
    a = archives.get_archive(archive)

    x, total_pages = DATABASE.get_state(user, archive)

    m = utils.PAGE_NUM_REGEX.search(filename)
    cur_page = int(m.group(1)) if m else 0
    Log.Info('{}: <{}> ({}/{})'.format(user, os.path.basename(archive), cur_page, total_pages))

    if cur_page > 0:
        DATABASE.set_state(user, archive, cur_page)

    return DataObject(utils.img_data(a, filename), utils.mime_type(filename))


@route(PREFIX + '/getthumb', archive=unicode)
def get_thumb(archive, filename):
    """Return the contents of `filename` from within `archive`."""
    a = archives.get_archive(archive)
    return DataObject(utils.img_data(a, filename), utils.mime_type(filename))


@route(PREFIX + '/getcover', archive=unicode)
def get_cover(archive):
    """Return the contents of the first file in `archive`."""
    a = archives.get_archive(archive)
    x = sorted([x for x in a.namelist() if splitext(x)[-1] in utils.IMAGE_FORMATS])
    if x:
        return DataObject(utils.img_data(a, x[0]), utils.mime_type(x[0]))


def Start():
    ObjectContainer.title1 = NAME


@handler(PREFIX, NAME)
def MainMenu():
    DATABASE.ensure_keys()

    archives.init_rar(Prefs['unrar'])
    archives.init_sz(Prefs['seven_zip'])

    user = DATABASE.get_user(Request.Headers.get('X-Plex-Token', 'default'))
    Log.Info('USER: {}'.format(user))

    oc = ObjectContainer(title2=unicode(user), no_cache=True)
    if bool(Prefs['update']):
        Updater(PREFIX + '/updater', oc)

    for x in BrowseDir(Prefs['cb_path'], page_size=int(Prefs['page_size']), user=user).objects:
        oc.add(x)
    return oc


@route(PREFIX + '/browse', page_size=int, offset=int)
def BrowseDir(cur_dir, page_size=20, offset=0, user=None):
    """Browse directories, with paging. Show directories and compatible archives."""
    oc = ObjectContainer(title2=unicode(os.path.basename(cur_dir)), no_cache=True)
    try:
        dir_list = utils.filtered_listdir(cur_dir)
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
            state = DATABASE.read(user, full_path)
            title = os.path.splitext(item)[0]
            oc.add(DirectoryObject(
                key=Callback(ComicMenu, archive=full_path, title=title, user=user),
                title=unicode(utils.decorate_title(full_path, user, state, title)),
                thumb=utils.thumb_transcode(Callback(get_cover, archive=full_path))))

    if offset + page_size < len(dir_list):
        oc.add(NextPageObject(key=Callback(BrowseDir, cur_dir=cur_dir,
                              page_size=page_size, offset=offset + page_size, user=user)))
    return oc


@route(PREFIX + '/comic/menu', archive=unicode)
def ComicMenu(archive, title, user=None):
    """The 'main menu' for a comic. this allows for different functions to be added."""
    oc = ObjectContainer(title2=unicode(os.path.basename(archive)), no_cache=True)
    state = DATABASE.read(user, archive)
    # Full comic
    oc.add(PhotoAlbumObject(
        key=Callback(Comic, archive=archive, user=user),
        rating_key=hashlib.md5(archive).hexdigest(),
        title=unicode(utils.decorate_title(archive, user, state, title)),
        thumb=utils.thumb_transcode(Callback(get_cover,
                                             archive=archive))))
    # Resume
    if state == utils.State.IN_PROGRESS:
        cur, total = DATABASE.get_state(user, archive)
        if cur > 0:
            oc.add(PhotoAlbumObject(title=unicode(L('resume')), thumb=R('resume.png'),
                                    key=Callback(Comic, archive=archive, user=user, page=cur),
                                    rating_key=hashlib.md5('{}{}'.format(archive, cur)).hexdigest()))
    # Read/Unread toggle
    if state == utils.State.UNREAD or state == utils.State.IN_PROGRESS:
        oc.add(DirectoryObject(title=unicode(L('mark_read')), thumb=R('mark-read.png'),
                               key=Callback(MarkRead, user=user, archive=archive)))
    else:
        oc.add(DirectoryObject(title=unicode(L('mark_unread')), thumb=R('mark-unread.png'),
                               key=Callback(MarkUnread, user=user, archive=archive)))
    return oc


@route(PREFIX + '/comic', archive=unicode, page=int)
def Comic(archive, user=None, page=0):
    """Return an oc with all pages in archive. if page > 0 return pages [page - Prefs['resume_length']:]"""
    oc = ObjectContainer(title2=unicode(os.path.basename(archive)), no_cache=True)
    try:
        a = archives.get_archive(archive)
    except archives.ArchiveError as e:
        Log.Error(e)
        return error_message('bad archive', 'unable to open archive: {}'.format(archive))
    for f in utils.sorted_nicely(a.namelist()):
        page_title, ext = utils.splitext(f)
        if not ext or ext not in utils.IMAGE_FORMATS:  # we're flattening the archive structure, so don't list the dirs.
            continue
        decoration = None
        if page > 0:
            m = utils.PAGE_NUM_REGEX.search(f)
            if m:
                page_num = int(m.group(1))
                if page_num < page - int(Prefs['resume_length']):
                    continue
                if page_num <= page:
                    decoration = '>'
        page_title = utils.basename(page_title)
        if decoration is not None:
            page_title = '{} {}'.format(decoration, page_title)

        if type(page_title) != unicode:
            try:
                page_title = page_title.decode('cp437')
            except Exception:
                try:
                    page_title = unicode(page_title, errors='replace')
                except Exception:
                    pass

        oc.add(CreatePhotoObject(
            media_key=Callback(GetImage, archive=String.Encode(archive),
                               filename=String.Encode(f), user=user, extension=ext.lstrip('.'),
                               time=int(time.time()) if bool(Prefs['prevent_caching']) else 0),
            rating_key=hashlib.sha1('{}{}{}'.format(archive, f, user)).hexdigest(),
            title=page_title,
            thumb=utils.thumb_transcode(Callback(get_thumb, archive=archive,
                                                 filename=f))))
    return oc


@route(PREFIX + '/markread')
def MarkRead(user, archive):
    Log.Info('Mark read. {} a={}'.format(user, archive))
    DATABASE.mark_read(user, archive)
    return error_message('marked', 'marked')


@route(PREFIX + '/markunread')
def MarkUnread(user, archive):
    Log.Info('Mark unread. a={}'.format(archive))
    DATABASE.mark_unread(user, archive)
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
    return get_image(String.Decode(archive), String.Decode(filename), user)
