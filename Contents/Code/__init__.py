# ComicReader v0.1 by Cory <babylonstudio@gmail.com>
# Supporting CBR, CBZ
# unrar binary loading based on https://github.com/sharkone/BitTorrent.bundle

import os


NAME = 'ComicReader'
PREFIX = '/photos/comicreader'


def Start():
    Route.Connect(PREFIX + '/getimage', SharedCodeService.formats.get_image)
    Route.Connect(PREFIX + '/getcover', SharedCodeService.formats.get_cover)
    SharedCodeService.formats.init_rar(Core.bundle_path)
    ObjectContainer.title1 = NAME


@handler(PREFIX, NAME)
def MainMenu():
    return BrowseDir(Prefs['cb_path'])


@route(PREFIX + '/browse')
def BrowseDir(cur_dir):
    oc = ObjectContainer()
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
                                   title=os.path.splitext(item)[0],
                                   thumb=Callback(SharedCodeService.formats.get_cover,
                                                  archive=full_path,
                                                  fmt=fmt)))
    return oc


@route(PREFIX + '/comic')
def Comic(archive, fmt):
    oc = ObjectContainer(title2=unicode(archive))
    a = SharedCodeService.formats.get_archive(archive, fmt)
    for f in a.namelist():
        if f.endswith('/'):
            continue
        Log.Info(f)
        oc.add(PhotoObject(url='comicreader://{}|{}|{}'.format(archive, f, fmt),
                           title=unicode(f),
                           thumb=Callback(SharedCodeService.formats.get_image,
                                          archive=archive,
                                          filename=f,
                                          fmt=fmt)
                           ))
    oc.objects.sort(key=lambda obj: obj.title)
    return oc
