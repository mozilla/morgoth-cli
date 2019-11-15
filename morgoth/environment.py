import os

import requests

from urllib.parse import urljoin


class Environment(object):
    _bearer_token = None
    _url = None
    _username = None
    _password = None

    def __init__(self, url, **kwargs):
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})

        self.url = url
        self.bearer_token = kwargs.get('bearer_token')

    def _reconfigure_session(self):
        self.session.headers.update({'Authorization': f'Bearer {self.bearer_token}'})

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
        self._reconfigure_session()

    @property
    def bearer_token(self):
        return self._bearer_token

    @bearer_token.setter
    def bearer_token(self, value):
        self._bearer_token = value
        self._reconfigure_session()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.url == other.url

    @classmethod
    def from_file(cls, path):
        with open(path, 'r') as f:
            return cls(f.read())

    def get_url(self, endpoint):
        return urljoin(self.url, '{}/{}'.format('api', endpoint))

    def request(self, endpoint, data=None, patch=False):
        url = self.get_url(endpoint)
        self.session.headers.update(({'Referer': url}))

        if data:
            if patch:
                response = self.session.patch(url, json=data, timeout=5)
            else:
                response = self.session.post(url, json=data, timeout=5)
        else:
            response = self.session.get(url, timeout=5)

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
