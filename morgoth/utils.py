import os
import tempfile

from colorama import Style

from morgoth.xpi import XPI


def output(str, *styles):
    print(Style.RESET_ALL, end='')
    if styles:
        print(*styles, end='')
    print(str, end='')
    print(Style.RESET_ALL)


def validate_uploaded_xpi_hash(local_xpi, bucket, remote_path):
    tmpdir = tempfile.mkdtemp()
    download_path = os.path.join(tmpdir, local_xpi.file_name)
    bucket.download_file(remote_path, download_path)
    uploaded_xpi = XPI(download_path)
    return uploaded_xpi.sha512sum == local_xpi.sha512sum
