import hashlib
import os
import tempfile
import zipfile

from xml.etree import ElementTree


PLATFORMS = {
    'Darwin_x86-gcc3-u-i386-x86_64': {
      'alias': 'default'
    },
    'Darwin_x86_64-gcc3-u-i386-x86_64': {
      'alias': 'default'
    },
    'Linux_x86-gcc3': {
      'alias': 'default'
    },
    'Linux_x86_64-gcc3': {
      'alias': 'default'
    },
    'WINNT_x86-msvc': {
      'alias': 'default'
    },
    'WINNT_x86-msvc-x64': {
      'alias': 'default'
    },
    'WINNT_x86-msvc-x86': {
      'alias': 'default'
    },
    'WINNT_x86_64-msvc': {
      'alias': 'default'
    },
    'WINNT_x86_64-msvc-x64': {
      'alias': 'default'
    },
}


class XPI(object):
    _hashed = None

    class DoesNotExist(Exception):
        pass

    class BadZipfile(zipfile.BadZipfile):
        pass

    class BadXPIfile(Exception):
        pass

    def __init__(self, path):
        if not os.path.isfile(path):
            raise XPI.DoesNotExist()

        self.path = path

        tmpdir = tempfile.mkdtemp()

        try:
            with zipfile.ZipFile(path, 'r') as zf:
                zf.extractall(tmpdir)
        except zipfile.BadZipfile:
            raise XPI.BadZipfile()

        rdf = ElementTree.parse(os.path.join(tmpdir, 'install.rdf'))
        description = rdf.getroot()[0]

        for child in description:
            if child.tag.endswith('id'):
                self.name = child.text

            if child.tag.endswith('version'):
                self.version = child.text

        if not self.name or not self.version:
            raise XPI.BadXPIfile()

    @property
    def release_name(self):
        return '{}-{}'.format(self.name, self.version)

    @property
    def short_name(self):
        return self.name.split('@')[0]

    @property
    def file_name(self):
        return '{}-signed.xpi'.format(self.release_name)

    @property
    def file_size(self):
        return os.path.getsize(self.path)

    @property
    def sha512sum(self):
        if not self._hashed:
            with open(self.path, 'rb') as f:
                self._hashed = hashlib.sha512(f.read()).hexdigest()
        return self._hashed

    def get_ftp_path(self, prefix):
        return os.path.join(prefix, self.short_name, self.file_name)

    def generate_release_data(self, base_url, prefix):
        platforms = PLATFORMS
        platforms.update({
            'default': {
                'fileUrl': '{}{}'.format(base_url, self.get_ftp_path(prefix)),
                'filesize': self.file_size,
                'hashValue': self.sha512sum,
            }
        })

        return {
            'addons': {
                self.name: {
                    'platforms': platforms,
                    'version': self.version,
                }
            },
            'hashFunction': 'sha512',
            'name': self.release_name,
            'product': 'SystemAddons',
            'schema_version': 5000,
        }
