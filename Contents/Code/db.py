import os
import hashlib
import utils
import archives
import difflib


def retrieve_username(token):
    """retrieve the username for the given access token from plex.tv"""
    access_tokens = XML.ElementFromURL(
        'https://plex.tv/servers/{}/access_tokens.xml?auth_token={}'.format(
            Core.get_server_attribute('machineIdentifier'), os.environ['PLEXTOKEN']),
        cacheTime=CACHE_1HOUR)
    for child in access_tokens.getchildren():
        if child.get('token') == token:
            username = child.get('username')
            return username if username else child.get('title')
    # couldn't get a username, use hash of the token.
    return hashlib.sha1(token).hexdigest()


class DictDB(object):

    def __init__(self):
        Dict['_load'] = True
        self.version = '1.0.0'
        if 'db_version' in Dict:
            self.version = Dict['db_version']

    def ensure_keys(self):
        Dict['_load'] = True  # make sure it's loaded so hopefully we don't overwrite...
        if 'usernames' not in Dict:
            Dict['usernames'] = {}
        if 'read_states' not in Dict:
            Dict['read_states'] = {}

    def get_user(self, token):
        """return a username from a plex access token. This will be the key for identifying the user."""
        h = hashlib.sha1(token).hexdigest()
        try:
            if h in Dict['usernames']:
                user = Dict['usernames'][h]
            else:
                Dict['usernames'][h] = retrieve_username(token)
                Dict.Save()
                user = Dict['usernames'][h]
        except Exception as e:
            Log.Error('get_session_identifier: {}'.format(e))
            user = h
        if user not in Dict['read_states']:
            Dict['read_states'][user] = {}
        return user

    def get_page_state(self, user, archive_path):
        """return a tuple (current page, total pages) for an archive for the user."""
        key = unicode(archive_path)
        if user not in Dict['read_states'] or key not in Dict['read_states'][user]:
            cur, total = (-1, -1)
        else:
            cur, total = Dict['read_states'][user][key]
        if total <= 0:
            a = archives.get_archive(archive_path)
            total = len([x for x in a.namelist() if utils.splitext(x)[-1] in utils.IMAGE_FORMATS])
        return (int(cur), int(total))

    def set_page_state(self, user, archive_path, page):
        """set the current page of archive for user."""
        cur_page, total_pages = self.get_page_state(user, archive_path)
        initial_state = self.comic_read_state(user, archive_path)
        try:
            Dict['read_states'][user][unicode(archive_path)] = (page, total_pages)
        except Exception:
            Log.Error('unable to write state.')
        else:
            new_state = self.comic_read_state(user, archive_path)
            if initial_state != new_state:
                self.P_update_tree(user, archive_path)
            Dict.Save()

    def mark_read(self, user, archive_path):
        """mark an archive as read for user. (set its page tuple to (n, n))."""
        state = self.get_page_state(user, archive_path)
        new_state = (state[1], state[1])
        Dict['read_states'][user][unicode(archive_path)] = new_state
        self.P_update_tree(user, archive_path)
        Dict.Save()

    def mark_unread(self, user, archive_path):
        """mark an archive as unread for user. (remove it from the database)."""
        try:
            del Dict['read_states'][user][unicode(archive_path)]
            self.P_update_tree(user, archive_path)
        except Exception as e:
            Log.Error('could not mark unread. {}'.format(str(e)))
        else:
            Dict.Save()

    def comic_read_state(self, user, archive_path, fuzz=5):
        """return the users read state of an archive. This is a simple enum."""
        key = unicode(archive_path)
        if user not in Dict['read_states'] or key not in Dict['read_states'][user]:
            return utils.State.UNREAD
        else:
            cur, total = Dict['read_states'][user][key]
        return utils.State.READ if abs(total - cur) < fuzz else utils.State.IN_PROGRESS

    def dir_read_state(self, user, directory, force=False):
        """return the users read state of directory. set force to not load from cache."""
        if directory in Dict['read_states'][user] and not force:
            Log.Debug('Loading series state from cache. {}'.format(directory))
            return Dict['read_states'][user][directory]
        Log.Debug('Calculating new series state. {}'.format(directory))
        states = set()
        dir_state = None
        for x, is_dir in utils.filtered_listdir(directory):
            state = (self.dir_read_state(user, os.path.join(directory, x), force) if is_dir else
                     self.comic_read_state(user, os.path.join(directory, x)))
            states.add(state)
            if len(states) > 1:
                dir_state = utils.State.IN_PROGRESS
                break
        if not states:
            dir_state = utils.State.UNREAD
        elif dir_state is None:
            dir_state = states.pop()

        Dict['read_states'][user][directory] = dir_state
        return dir_state

    def P_update_tree(self, user, archive_path):  # private, plex can't use _var
        """update the cache of the dir read state for everything between cb_path and archive_path."""
        Log.Debug('updating tree {}'.format(archive_path))
        base = Prefs['cb_path']
        x = difflib.SequenceMatcher(a=base, b=archive_path)
        for tag, i1, i2, j1, j2 in x.get_opcodes():
            if tag == 'insert':
                try:
                    diff = os.path.split(archive_path[j1:j2])[0]
                    d = diff.replace('\\', '/').split('/')[1]
                    path = os.path.join(base, d)
                    Log.Debug('archive root: {}'.format(path))
                    if os.path.abspath(base) == os.path.abspath(path):
                        Log.Debug('item is in root dir. skipping.')
                    else:
                        state = self.dir_read_state(user, path, True)
                except Exception as e:
                    Log.Error('P_update_tree {}'.format(e))
                return


DATABASE = DictDB()
