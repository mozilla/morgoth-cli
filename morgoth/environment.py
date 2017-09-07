import base64
import os

from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


class Environment(object):
    url = None
    username = None
    password = None

    def __init__(self, url, **kwargs):
        self.url = self._normalize_url(url)
        self.username = kwargs.get('username', None)
        self.password = kwargs.get('password', None)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.url == other.url

    @classmethod
    def from_file(cls, path):
        with open(path, 'r') as f:
            return cls(f.read())

    @staticmethod
    def _normalize_url(url):
        stripped = url.strip('\n\t\r /')
        return '{}/'.format(stripped)

    def get_url(self, endpoint):
        return '{}api/{}'.format(self.url, endpoint)

    def request(self, endpoint, **kwargs):
        request = Request(self.get_url(endpoint), **kwargs)

        if self.username and self.password:
            auth = base64.encodebytes('{}:{}'.format(self.username, self.password).encode())
            auth = auth.decode().replace('\n', '')
            request.add_header('Authorization', 'Basic {}'.format(auth))

        return urlopen(request)

    def validate(self):
        try:
            response = self.request('rules')
        except HTTPError as err:
            if err.code == 401:
                raise
            return False
        except (URLError, ValueError):
            return False

        return response.code == 200 and response.getheader('Content-Type') == 'application/json'

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(self.url)
