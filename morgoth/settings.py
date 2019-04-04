import configparser

from morgoth import CONFIG_PATH


class Settings(object):
    _path = None

    def __init__(self, path):
        self.config = configparser.ConfigParser()
        self.path = path

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        if value != self._path:
            self._path = value
            with open(self._path, 'a+') as f:
                f.seek(0)
                self.config.read_file(f)

    @staticmethod
    def _parse_key(key):
        keys = key.split('.', 1)
        if len(keys) < 2:
            keys = ['morgoth'] + keys
        return keys

    def get(self, key, default=None):
        keys = self._parse_key(key)

        try:
            value = self.config[keys[0]][keys[1]]
        except KeyError:
            return default

        return value

    def _set(self, key, value):
        keys = self._parse_key(key)

        if not keys[0] in self.config:
            self.config[keys[0]] = {}

        self.config[keys[0]][keys[1]] = value

    def set(self, key, value):
        keys = self._parse_key(key)
        self._set(key, value)

    def delete(self, key):
        keys = self._parse_key(key)
        del self.config[keys[0]][keys[1]]

    def save(self):
        with open(self.path, 'w') as f:
            self.config.write(f)


try:
    settings = Settings(CONFIG_PATH)
except FileNotFoundError:
    settings = Settings(None)
