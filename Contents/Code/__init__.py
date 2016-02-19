# ComicReader v0.1 by Cory <babylonstudio@gmail.com>
# Supporting CBR, CBZ
# unrar binary loading based on https://github.com/sharkone/BitTorrent.bundle

import os
import stat
import platform
from glob import glob
import rarfile
import zipfile



NAME = 'ComicReader'
PREFIX = '/photos/comicreader'


class Formats(object):
    CBR = 'cbr'
    CBZ = 'cbz'


def Start():
    ObjectContainer.title1 = NAME
    rarfile.UNRAR_TOOL = get_rar_dir()
    try:
        os.chmod(rarfile.UNRAR_TOOL, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    except Exception as e:
        Log.Error(e)
    Log.Info('USING UNRAR EXECUTABLE: {}'.format(rarfile.UNRAR_TOOL))


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
                fmt = Formats.CBR
            elif item.endswith('.cbz'):
                fmt = Formats.CBZ
            else:
                continue
            oc.add(DirectoryObject(key=Callback(Comic, archive=full_path,
                                                fmt=fmt),
                                   title=os.path.splitext(item)[0],
                                   thumb=Callback(GetCover, archive=full_path,
                                                  fmt=fmt)))
    return oc


@route(PREFIX + '/comic')
def Comic(archive, fmt):
    oc = ObjectContainer(title2=unicode(archive))
    a = get_archive(archive, fmt)
    for f in a.namelist():
        if f.endswith('/'):
            continue
        Log.Info(f)
        oc.add(PhotoObject(key=Callback(GetImage, archive=archive, filename=f,
                                        fmt=fmt),
                           rating_key=f,
                           title=unicode(f),
                           thumb=Callback(GetImage, archive=archive, filename=f,
                                          fmt=fmt)))
    oc.objects.sort(key=lambda obj: obj.title)
    return oc


@route(PREFIX + '/getimage')
def GetImage(archive, filename, fmt):
    # works on OpenPHT, PMP, Plex Web, Android. *Not iOS
    a = get_archive(archive, fmt)
    return DataObject(a.read(filename), mime_type(filename))


@route(PREFIX + '/getcover')
def GetCover(archive, fmt):
    a = get_archive(archive, fmt)
    x = sorted([x for x in a.namelist() if not x.endswith('/')])
    try:
        cover = x[0]
    except IndexError:
        return None
    else:
        return DataObject(a.read(cover), mime_type(cover))


def mime_type(filename):
    ext = os.path.splitext(filename)[-1]
    return {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.tiff': 'image/tiff',
        '.bmp': 'image/bmp'
    }[ext]


def get_archive(archive, fmt):
    if fmt == Formats.CBR:
        return rarfile.RarFile(archive)
    elif fmt == Formats.CBZ:
        return zipfile.ZipFile(archive)
    else:
        return None


def get_rar_dir():
    base_dir = os.path.abspath(os.path.join(Core.bundle_path, 'Contents', 'bin'))
    if Platform.OS == 'MacOSX':
        return os.path.join(base_dir, 'darwin_amd64', 'unrar')
    elif Platform.OS == 'Linux':
        arch = platform.architecture()[0]
        if arch == '64bit':
            return os.path.join(base_dir, 'linux_amd64', 'unrar')
        elif arch == '32bit':
            return os.path.join(base_dir, 'linux_386', 'unrar')
    elif Platform.OS == 'Windows':
        return os.path.join(base_dir, 'windows_386', 'unrar.exe')
