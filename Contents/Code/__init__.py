# ComicReader v0.1 by Cory <babylonstudio@gmail.com>
# Supporting CBR, CBZ
# unrar binary loading based on https://github.com/sharkone/BitTorrent.bundle

import os
import json
from io import open

NAME = 'ComicReader'
PREFIX = '/photos/comicreader'


def Start():
    Route.Connect(PREFIX + '/getimage', SharedCodeService.formats.get_image)
    Route.Connect(PREFIX + '/getthumb', SharedCodeService.formats.get_thumb)
    Route.Connect(PREFIX + '/getcover', SharedCodeService.formats.get_cover)
    SharedCodeService.formats.init_rar(Core.bundle_path)
    ObjectContainer.title1 = NAME


@handler(PREFIX, NAME)
def MainMenu():
    SharedCodeService.formats.init_sz(Prefs['seven_zip'])
    oc = ObjectContainer(no_cache=True)
    if bool(Prefs['resume']) and os.path.isfile(SharedCodeService.formats.DB_FILE):
        with open(SharedCodeService.formats.DB_FILE, 'r') as f:
            db = json.loads(f.read())
            sid = get_session_identifier()
            if sid in db:
                try:
                    archive, filename = db[sid]
                except:
                    archive, filename, fmt = db[sid]
                title = archive.split('/')[-1].split('\\')[-1]
                oc.add(DirectoryObject(key=Callback(Comic, archive=archive, filename=filename),
                                       title='>> resume {}'.format(title),
                                       thumb=Callback(SharedCodeService.formats.get_cover,
                                                      archive=archive)))
    for x in BrowseDir(Prefs['cb_path']).objects:
        oc.add(x)
    return oc


def error_message(error, message):
    Log.Error("ComicReader: {} - {}".format(error, message))
    return MessageContainer(header=unicode(error), message=unicode(message))


def get_session_identifier():
    # token is prob not reliable but good enough for now
    try:
        return Request.Headers['X-Plex-Token']
    except Exception:
        return 'none'


@route(PREFIX + '/browse')
def BrowseDir(cur_dir):
    oc = ObjectContainer(no_cache=True)
    try:
        dir_list = os.listdir(cur_dir)
    except Exception:
        return ObjectContainer(header='bad path', message='bad path')
    for item in dir_list:
        full_path = os.path.join(cur_dir, item)
        if os.path.isdir(full_path):
            oc.add(DirectoryObject(key=Callback(BrowseDir, cur_dir=full_path),
                                   title=item))
        else:
            if os.path.splitext(item)[-1] not in SharedCodeService.formats.FORMATS:
                continue
            oc.add(PhotoAlbumObject(key=Callback(Comic, archive=full_path),
                                    rating_key=full_path,
                                    title=unicode(os.path.splitext(item)[0]),
                                    thumb=Callback(SharedCodeService.formats.get_cover,
                                                   archive=full_path)))
    return oc


@route(PREFIX + '/comic')
def Comic(archive, filename=None):
    oc = ObjectContainer(title2=unicode(archive), no_cache=True)
    try:
        a = SharedCodeService.formats.get_archive(archive)
    except SharedCodeService.formats.ArchiveError as e:
        Log.Error(str(e))
        return error_message('bad archive', 'bad archive')
    files = sorted(a.namelist())
    if filename is not None:
        pos = files.index(filename)
        files = files[max(0, pos - 3):]
    for f in files:
        if f.endswith('/'):
            continue
        Log.Info(f)
        page = f.split('/')[-1] if '/' in f else f
        oc.add(PhotoObject(url=SharedCodeService.formats.build_url(archive, f, get_session_identifier()),
                           title=unicode(page) if f != filename else '>> {}'.format(page),
                           thumb=Callback(SharedCodeService.formats.get_thumb,
                                          archive=archive,
                                          filename=f)))
    return oc
