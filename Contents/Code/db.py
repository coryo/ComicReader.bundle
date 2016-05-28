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
    return token


class DictDB(object):

    def __init__(self):
        Dict['_load'] = True
        self.version = '1.0.0'
        if 'db_version' in Dict:
            self.version = Dict['db_version']

    def ensure_keys(self):
        Dict['_load'] = True
        if 'usernames' not in Dict:
            Dict['usernames'] = {}
        if 'read_states' not in Dict:
            Dict['read_states'] = {}

    def get_user(self, token):
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

    def get_state(self, user, archive_path):
        key = unicode(archive_path)
        if user not in Dict['read_states'] or key not in Dict['read_states'][user]:
            cur, total = (-1, -1)
        else:
            cur, total = Dict['read_states'][user][key]
        if total <= 0:
            a = archives.get_archive(archive_path)
            total = len([x for x in a.namelist() if utils.splitext(x)[-1] in utils.IMAGE_FORMATS])
        return (int(cur), int(total))

    def set_state(self, user, archive_path, page):
        cur_page, total_pages = self.get_state(user, archive_path)
        initial_state = self.comic_state(user, archive_path)
        try:
            Dict['read_states'][user][unicode(archive_path)] = (page, total_pages)
        except Exception:
            Log.Error('unable to write state.')
        else:
            new_state = self.comic_state(user, archive_path)
            if initial_state != new_state:
                self.update_tree(user, archive_path)
            Dict.Save()

    def read(self, user, archive_path, fuzz=5):
        cur, total = self.get_state(user, archive_path)
        if cur < 0 or total < 0:
            return utils.State.UNREAD
        return utils.State.READ if abs(total - cur) < fuzz else utils.State.IN_PROGRESS

    def mark_read(self, user, archive_path):
        state = self.get_state(user, archive_path)
        new_state = (state[1], state[1])
        Dict['read_states'][user][unicode(archive_path)] = new_state
        self.update_tree(user, archive_path)
        Dict.Save()

    def mark_unread(self, user, archive_path):
        try:
            del Dict['read_states'][user][unicode(archive_path)]
            self.update_tree(user, archive_path)
        except Exception as e:
            Log.Error('could not mark unread. {}'.format(str(e)))
        else:
            Dict.Save()

    def comic_state(self, user, archive_path, fuzz=5):
        key = unicode(archive_path)
        if user not in Dict['read_states'] or key not in Dict['read_states'][user]:
            return utils.State.UNREAD
        else:
            cur, total = Dict['read_states'][user][key]
        return utils.State.READ if abs(total - cur) < fuzz else utils.State.IN_PROGRESS

    def series_state(self, user, directory, force=False):
        if directory in Dict['read_states'][user] and not force:
            Log.Info('Loading series state from cache.')
            return Dict['read_states'][user][directory]
        Log.Info('Calculating new series state.')
        states = set([
            (self.series_state(user, os.path.join(directory, x), force) if is_dir else
             self.comic_state(user, os.path.join(directory, x)))
            for x, is_dir in utils.filtered_listdir(directory)
        ])
        if not states:
            sstate = utils.State.UNREAD
        sstate = states.pop() if len(states) == 1 else utils.State.IN_PROGRESS
        Dict['read_states'][user][directory] = sstate
        return sstate

    def update_tree(self, user, archive_path):
        Log.Info('updating tree {}'.format(archive_path))
        base = Prefs['cb_path']
        x = difflib.SequenceMatcher(a=base, b=archive_path)
        for tag, i1, i2, j1, j2 in x.get_opcodes():
            if tag == 'insert':
                try:
                    diff = os.path.split(archive_path[j1:j2])[0]
                    d = diff.replace('\\', '/').split('/')[1]
                    path = os.path.join(base, d)
                    Log.Info(path)
                    state = self.series_state(user, path, True)
                    Log.Info(state)
                    return
                except Exception as e:
                    Log.Error('update_tree {}'.format(e))


DATABASE = DictDB()
