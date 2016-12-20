# ComicReader.bundle by Cory Parsons <babylonstudio@gmail.com>
# https://github.com/coryo/ComicReader.bundle
# Supporting CBR, CBZ, CB7

import os
import hashlib
import random
import re
import time
from io import open
from __builtin__ import globals

from updater import Updater
import utils
import archives
from db import DATABASE, test_token

NAME = 'ComicReader'
PREFIX = '/photos/comicreader'


def error_message(error, message):
    Log.Error("ComicReader: {} - {}".format(error, message))
    return MessageContainer(header=unicode(error), message=unicode(message))


def Start():
    ObjectContainer.title1 = NAME


@route(PREFIX + '/db')
def Db():
    return utils.JSONResponse(DATABASE.dumps())


@route(PREFIX + '/db/clean')
def DbClean():
    return utils.JSONResponse(JSON.StringFromObject(DATABASE.clean_states()))


@route(PREFIX + '/users')
def Users():
    oc = ObjectContainer(no_cache=True)
    for username in DATABASE.usernames():
        oc.add(DirectoryObject(key=Callback(SwitchUser, new_username=username),
                               title='Switch to: {}'.format(username),
                               thumb=R('icon-default.png')))

    oc.add(DirectoryObject(key=Callback(ClearUsers), title='Clear username cache.',
                           thumb=R('icon-default.png')))
    oc.add(DirectoryObject(key=Callback(RefreshUser), title='Refresh User.',
                           thumb=R('icon-default.png')))
    return oc


@route(PREFIX + '/users/refresh')
def RefreshUser():
    DATABASE.get_user(Request.Headers.get('X-Plex-Token', 'default'), force=True)
    return error_message('refreshed user', 'refreshed user')


@route(PREFIX + '/users/clear')
def ClearUsers():
    DATABASE.clear_usernames()
    return error_message('cleared cache', 'cleared cache')


@route(PREFIX + '/users/switch')
def SwitchUser(new_username):
    DATABASE.switch_user(Request.Headers.get('X-Plex-Token', 'default'), new_username)
    return error_message('changed user', 'changed user')


@handler(PREFIX, NAME)
def MainMenu():
    DATABASE.ensure_keys()
    Log.Debug('test_token: {}'.format(test_token(Request.Headers.get('X-Plex-Token'))))

    archives.init_rar(Prefs['unrar'])
    archives.init_sz(Prefs['seven_zip'])

    user = DATABASE.get_user(Request.Headers.get('X-Plex-Token', 'default'))
    Log.Info('USER: {}'.format(user))

    oc = ObjectContainer(title2=unicode(user), no_cache=True)

    if bool(Prefs['update']):
        Updater(PREFIX + '/updater', oc)

    oc.add(DirectoryObject(key=Callback(Users), title='Hello {}. Switch User?'.format(user),
                           thumb=R('icon-default.png')))

    browse_dir = BrowseDir(Prefs['cb_path'], page_size=int(Prefs['page_size']), user=user)
    if not hasattr(browse_dir, 'objects'):
        return browse_dir
    for x in browse_dir.objects:
        oc.add(x)
    return oc


@route(PREFIX + '/browse', page_size=int, offset=int)
def BrowseDir(cur_dir, page_size=20, offset=0, user=None):
    """Browse directories, with paging. Show directories and compatible archives."""
    t1 = time.time()
    oc = ObjectContainer(title2=unicode(os.path.basename(cur_dir)), no_cache=True)
    try:
        dir_list = utils.filtered_listdir(cur_dir)
        page = dir_list[offset:offset + page_size]
    except Exception as e:
        Log.Error('BrowseDir: failed to get directory listing.')
        Log.Error('BrowseDir: {}, cur_dir={}, page_size={}, offset={}, user={}'.format(
            e, cur_dir, page_size, offset, user))
        return error_message('bad path', 'bad path')

    # Read/Unread toggle
    if os.path.abspath(cur_dir) != os.path.abspath(Prefs['cb_path']):
        oc.add(DirectoryObject(title=unicode(L('mark_all_read')), thumb=R('mark-read.png'),
                                key=Callback(Confirmation, f='MarkReadDir', action=L('mark_all_read'), user=user, path=cur_dir)))
        oc.add(DirectoryObject(title=unicode(L('mark_all_unread')), thumb=R('mark-unread.png'),
                                key=Callback(Confirmation, f='MarkUnreadDir', action=L('mark_all_unread'), user=user, path=cur_dir)))        
    for item, is_dir in page:
        full_path = os.path.join(cur_dir, item)
        if is_dir:
            state = DATABASE.dir_read_state(user, full_path)
            oc.add(DirectoryObject(
                key=Callback(BrowseDir, cur_dir=full_path, page_size=page_size, user=user),
                title=unicode(utils.decorate_directory(user, state, item)),
                thumb=R('folder.png')))
        else:
            state = DATABASE.comic_read_state(user, full_path)
            title = os.path.splitext(item)[0]
            oc.add(DirectoryObject(
                key=Callback(ComicMenu, archive_path=full_path, title=title, user=user),
                title=unicode(utils.decorate_title(full_path, user, state, title)),
                thumb=utils.thumb_transcode(Callback(get_cover, archive_path=full_path))))

    if offset + page_size < len(dir_list):
        oc.add(NextPageObject(key=Callback(BrowseDir, cur_dir=cur_dir,
                              page_size=page_size, offset=offset + page_size, user=user)))
    t2 = time.time()
    Log.Info('Directory loaded in {:.0f} ms. {}'.format((t2 - t1) * 1000.0, cur_dir))
    return oc


@route(PREFIX + '/comic/menu', archive_path=unicode)
def ComicMenu(archive_path, title, user=None):
    """The 'main menu' for a comic. this allows for different functions to be added."""
    oc = ObjectContainer(title2=unicode(os.path.basename(archive_path)), no_cache=True)
    state = DATABASE.comic_read_state(user, archive_path)
    # Full comic
    oc.add(PhotoAlbumObject(
        key=Callback(Comic, archive_path=archive_path, user=user),
        rating_key=hashlib.md5(archive_path).hexdigest(),
        title=unicode(utils.decorate_title(archive_path, user, state, title)),
        thumb=utils.thumb_transcode(Callback(get_cover, archive_path=archive_path))))
    # Resume
    if state == utils.State.IN_PROGRESS:
        cur, total = DATABASE.get_page_state(user, archive_path)
        if cur > 0:
            oc.add(PhotoAlbumObject(title=unicode(L('resume')), thumb=R('resume.png'),
                                    key=Callback(Comic, archive_path=archive_path, user=user, page=cur),
                                    rating_key=hashlib.md5('{}{}'.format(archive_path, cur)).hexdigest()))
    # Read/Unread toggle
    if state == utils.State.UNREAD or state == utils.State.IN_PROGRESS:
        oc.add(DirectoryObject(title=unicode(L('mark_read')), thumb=R('mark-read.png'),
                               key=Callback(MarkRead, user=user, archive_path=archive_path)))
    else:
        oc.add(DirectoryObject(title=unicode(L('mark_unread')), thumb=R('mark-unread.png'),
                               key=Callback(MarkUnread, user=user, archive_path=archive_path)))
    return oc


@route(PREFIX + '/comic', archive_path=unicode, page=int)
def Comic(archive_path, user=None, page=0):
    """Return an oc with all pages in archive_path. if page > 0 return pages [page - Prefs['resume_length']:]"""
    oc = ObjectContainer(title2=unicode(os.path.basename(archive_path)), no_cache=True)
    try:
        archive = archives.get_archive(archive_path)
    except archives.ArchiveError as e:
        Log.Error(e)
        return error_message('bad archive', 'unable to open archive: {}'.format(archive_path))
    for f in utils.sorted_nicely(archive.namelist()):
        page_title, ext = utils.splitext(f)
        if not ext or ext.lower() not in utils.IMAGE_FORMATS:
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
            media_key=Callback(GetImage, archive_path=String.Encode(archive_path),
                               filename=String.Encode(f), user=user, extension=ext.lstrip('.'),
                               time=int(time.time()) if bool(Prefs['prevent_caching']) else 0),
            rating_key=hashlib.sha1('{}{}{}'.format(archive_path, f, user)).hexdigest(),
            title=page_title,
            thumb=utils.thumb_transcode(Callback(get_thumb, archive_path=archive_path,
                                                 filename=f))))
    return oc


@route(PREFIX + '/markread')
def MarkRead(user, archive_path):
    Log.Info('Mark read. {} a={}'.format(user, archive_path))
    DATABASE.mark_read(user, archive_path)
    return error_message('marked', 'marked')


@route(PREFIX + '/markunread')
def MarkUnread(user, archive_path):
    Log.Info('Mark unread. a={}'.format(archive_path))
    DATABASE.mark_unread(user, archive_path)
    return error_message('marked', 'marked')

@route(PREFIX + '/markreaddir')
def MarkReadDir(user, path):
    Log.Info('Mark read. {} a={}'.format(user, path))
    DATABASE.mark_read_dir(user, path)
    return error_message('marked', 'marked')


@route(PREFIX + '/markunreaddir')
def MarkUnreadDir(user, path):
    Log.Info('Mark unread. a={}'.format(path))
    DATABASE.mark_unread_dir(user, path)
    return error_message('marked', 'marked')

@route(PREFIX + '/confirm')
def Confirmation(f, action, **kwargs):
    function = globals()[f]
    oc = ObjectContainer(title2=action)
    oc.add(DirectoryObject(title=unicode('{} {}'.format(L('confirm'), action)), thumb=R('icon-default.png'),
                           key=Callback(function, **kwargs)))
    return oc


@route(PREFIX + '/createphotoobject')
def CreatePhotoObject(rating_key, title, thumb, media_key=None):
    """simulate a url service"""
    po = PhotoObject(
        key=Callback(CreatePhotoObject, rating_key=rating_key, title=title, thumb=thumb),
        rating_key=rating_key, title=title, thumb=thumb)
    if media_key:
        po.add(MediaObject(parts=[PartObject(key=media_key)]))
    return po


@route(PREFIX + '/image/{user}/{archive_path}/{filename}.{extension}', time=int)
def GetImage(archive_path, filename, user, extension, time=0):
    """direct response with image data. setting a new time value should prevent
    clients from loading their cached copy so our page tracking code can run."""
    return get_image(String.Decode(archive_path), String.Decode(filename), user)


@route(PREFIX + '/getimage', archive_path=unicode)
def get_image(archive_path, filename, user):
    """Return the contents of `filename` from within `archive_path`. also do some other stuff."""
    archive = archives.get_archive(archive_path)

    x, total_pages = DATABASE.get_page_state(user, archive_path)

    m = utils.PAGE_NUM_REGEX.search(filename)
    cur_page = int(m.group(1)) if m else 0
    Log.Info('{}: <{}> ({}/{})'.format(user, os.path.basename(archive_path), cur_page, total_pages))

    if cur_page > 0:
        DATABASE.set_page_state(user, archive_path, cur_page)

    return utils.data_object(archive, filename)


@route(PREFIX + '/getthumb', archive_path=unicode)
def get_thumb(archive_path, filename):
    """Return the contents of `filename` from within `archive_path`."""
    archive = archives.get_archive(archive_path)
    return utils.data_object(archive, filename)


@route(PREFIX + '/getcover', archive_path=unicode)
def get_cover(archive_path):
    """Return the contents of the first file in `archive_path`."""
    archive = archives.get_archive(archive_path)
    x = sorted([x for x in archive.namelist() if utils.splitext(x)[-1].lower() in utils.IMAGE_FORMATS])
    if x:
        return utils.data_object(archive, x[0])
