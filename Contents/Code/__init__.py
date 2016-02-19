# ComicReader v0.1 by Cory <babylonstudio@gmail.com>
# Supporting CBR, CBZ
# unrar binary loading based on https://github.com/sharkone/BitTorrent.bundle

import os
import json
from __builtin__ import open

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
    oc = ObjectContainer(no_cache=True)
    with open(SharedCodeService.formats.DB_FILE, 'r') as f:
        db = json.loads(f.read())
        if Request.Headers['X-Plex-Token'] in db:
            archive, filename, fmt = db[Request.Headers['X-Plex-Token']]
            title = archive.split('/')[-1].split('\\')[-1]
            oc.add(DirectoryObject(key=Callback(Comic, archive=archive, fmt=fmt, filename=filename), title='>> resume {}'.format(title)))
    for x in BrowseDir(Prefs['cb_path']).objects:
        oc.add(x)
    return oc


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
            if item.endswith('.cbr'):
                fmt = SharedCodeService.formats.Formats.CBR
            elif item.endswith('.cbz'):
                fmt = SharedCodeService.formats.Formats.CBZ
            else:
                continue
            oc.add(DirectoryObject(key=Callback(Comic, archive=full_path,
                                                fmt=fmt),
                                   title='[{}] {}'.format(fmt, os.path.splitext(item)[0]),
                                   thumb=Callback(SharedCodeService.formats.get_cover,
                                                  archive=full_path,
                                                  fmt=fmt)))
    return oc


@route(PREFIX + '/comic')
def Comic(archive, fmt, filename=None):
    oc = ObjectContainer(title2=unicode(archive), no_cache=True)
    a = SharedCodeService.formats.get_archive(archive, fmt)
    files = sorted(a.namelist())
    if filename is not None:
        pos = files.index(filename)
        files = files[max(0, pos - 3):]
    for f in files:
        if f.endswith('/'):
            continue
        Log.Info(f)
        page = f.split('/')[-1] if '/' in f else f
        oc.add(PhotoObject(url='comicreader://{}|{}|{}|{}'.format(archive, f, fmt, Request.Headers['X-Plex-Token']),
                           title=unicode(page) if f != filename else '>> {}'.format(page),
                           thumb=Callback(SharedCodeService.formats.get_thumb,
                                          archive=archive,
                                          filename=f,
                                          fmt=fmt)))
    return oc
