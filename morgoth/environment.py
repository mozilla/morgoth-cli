import os

import requests

from urllib.parse import urljoin


class Environment(object):
    _url = None
    _username = None
    _password = None

    def __init__(self, url, **kwargs):
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})

        self.url = url
        self.username = kwargs.get('username', None)
        self.password = kwargs.get('password', None)

        self._reconfigure_session()

    def _reconfigure_session(self):
        self.session.auth = (self.username, self.password)

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
        self._reconfigure_session()

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        self._username = value
        self._reconfigure_session()

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = value
        self._reconfigure_session()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.url == other.url

    @classmethod
    def from_file(cls, path):
        with open(path, 'r') as f:
            return cls(f.read())

    def get_url(self, endpoint):
        return urljoin(self.url, '{}/{}'.format('api', endpoint))

    def request(self, endpoint, data=None):
        url = self.get_url(endpoint)

        if data:
            response = self.session.post(url, auth=(self.username, self.password), json=data,
                                         timeout=5)
        else:
            response = self.session.get(url, auth=(self.username, self.password), timeout=5)

        response.raise_for_status()

        return response

    def fetch(self, endpoint, **kwargs):
        response = self.request(endpoint, **kwargs)
        return response.json()

    def validate(self):
        response = self.request('rules')
        return response.status_code == 200 and response.headers['content-type']

    def csrf(self):
        return self.request('csrf_token').headers['x-csrf-token']

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(self.url)
