import rarfile
import zipfile
import szipfile


FORMATS = ['.cbr', '.cbz', '.cb7', '.zip', '.rar', '.7z']


def init_rar(path):
    """Set the unrar executable"""
    if path:
        rarfile.UNRAR_TOOL = os.path.abspath(path)
    Log.Info('USING UNRAR EXECUTABLE: {}'.format(rarfile.UNRAR_TOOL))


def init_sz(path):
    """Set the 7z executable"""
    if path:
        szipfile.SZ_TOOL = os.path.abspath(path)
    Log.Info('USING 7ZIP EXECUTABLE: {}'.format(szipfile.SZ_TOOL))


class ArchiveError(Exception):
    pass


def get_archive(archive):
    """Return an archive object.
    Some archives are given the wrong extension, so try opening it until it works."""
    try:
        return rarfile.RarFile(archive)
    except Exception:
        pass
    try:
        return zipfile.ZipFile(archive)
    except Exception:
        pass
    try:
        return szipfile.SZipFile(archive)
    except Exception:
        pass

    raise ArchiveError
