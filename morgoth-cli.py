#!/usr/bin/env python3

import os
import json
import tempfile

import boto3
import click

from colorama import Fore, Style

from morgoth.conf import settings
from morgoth.xpi import XPI


aws_settings = settings['aws']


def close(code):
    """An alias for exit that resets the terminal styling."""
    print(Style.RESET_ALL)
    exit(code)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--profile', default=aws_settings.get('profile'))
@click.argument('xpi_file')
def mkrelease(xpi_file, profile):
    prefix = aws_settings['prefix']

    try:
        xpi = XPI(xpi_file)
    except XPI.DoesNotExist:
        print(Fore.RED + 'File does not exist.')
        close(1)
    except XPI.BadZipfile:
        print(Fore.RED + 'XPI cannot be unzipped.')
        close(1)
    except XPI.BadXPIfile:
        print(Fore.RED + 'XPI is not properly configured.')
        close(1)
    else:
        print(Fore.CYAN + 'Found: {}'.format(xpi.release_name))

        if not click.confirm(Style.RESET_ALL + 'Is this correct?'):
            print(Fore.RED + 'Release could not be auto-generated.')
            close(1)

        session = boto3.Session(profile_name=profile)
        s3 = session.resource('s3')
        bucket = s3.Bucket(settings.get('aws', {})['bucket_name'])

        exists = False
        for obj in bucket.objects.filter(Prefix=prefix):
            if obj.key == xpi.get_ftp_path(prefix):
                exists = True

        uploaded = False
        if exists:
            tmpdir = tempfile.mkdtemp()
            download_path = os.path.join(tmpdir, xpi.file_name)
            bucket.download_file(xpi.get_ftp_path(prefix), download_path)
            uploaded_xpi = XPI(download_path)

            if uploaded_xpi.sha512sum == xpi.sha512sum:
                print(Fore.GREEN + 'XPI already uploaded.')
                uploaded = True
            else:
                print(Fore.YELLOW + 'XPI with matching filename already uploaded.')

        if not uploaded:
            if exists and not click.confirm(Style.RESET_ALL + 'Would you like to replace it?'):
                print(Fore.RED + 'Aborting.')
                close(1)
            with open(xpi.path, 'rb') as data:
                bucket.put_object(Key=xpi.get_ftp_path(prefix), Body=data)
            print(Fore.GREEN + 'XPI uploaded successfully.')

        json_path = 'releases/{}.json'.format(xpi.release_name)

        if os.path.exists(json_path):
            print(Fore.YELLOW + 'Release JSON file already exists.')
            if not click.confirm(Style.RESET_ALL + 'Replace existing release JSON file?'):
                print(Fore.RED + 'Aborting.')
                close(1)

        print(Style.RESET_ALL + 'Saving to: {}{}'.format(Style.BRIGHT, json_path))

        os.makedirs('releases', exist_ok=True)
        with open(json_path, 'w') as f:
            f.write(json.dumps(
                xpi.generate_release_data(aws_settings['base_url'], prefix),
                indent=2, sort_keys=True))

    close(0)


@cli.command()
@click.argument('releases', nargs=-1)
def mksuperblob(releases):
    names = []

    for release in releases:
        with open(release, 'r') as f:
            release_data = json.loads(f.read())
        short_name = release_data['name'].split('@')[0]
        for k in release_data['addons']:
            if k.startswith(short_name):
                version = release_data['addons'][k]['version']
        names.append('{}-{}'.format(short_name, version))

    if not len(names):
        print(Fore.RED + 'No releases specified.')
        close(1)

    names.sort()

    sb_name = 'Superblob-{}'.format('-'.join(names))
    sb_data = {
      'blobs': names,
      'name': sb_name,
      'schema_version': 4000
    }

    sb_path = 'releases/superblobs/{}.json'.format(sb_name)
    os.makedirs('releases/superblobs', exist_ok=True)
    with open(sb_path, 'w') as f:
        f.write(json.dumps(sb_data, indent=2, sort_keys=True))

    print(Style.RESET_ALL + 'Saving to: {}{}'.format(Style.BRIGHT, sb_path))

    close(0)


if __name__ == '__main__':
    cli()
