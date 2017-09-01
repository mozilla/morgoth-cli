#!/usr/bin/env python3

import os
import json
import tempfile

import boto3
import click
import yaml

from colorama import Fore, Style

from morgoth.xpi import XPI


def quit(code):
    """An alias for exit that resets the terminal styling."""
    print(Style.RESET_ALL)
    exit(code)


if not os.path.exists('.morgoth.yml'):
    print(Fore.RED + 'Configuration file is missing.')
    quit(1)

with open('.morgoth.yml', 'r') as f:
    config = yaml.safe_load(f)
    BUCKET_NAME = config.get('bucket_name')
    PREFIX = config.get('prefix')
    BASE_URL = config.get('base_url')
    PROFILE = config.get('profile')


@click.group()
def cli():
    pass


@cli.command()
@click.option('--profile', default=PROFILE)
@click.argument('xpi_file')
def mkrelease(xpi_file, profile):
    try:
        xpi = XPI(xpi_file)
    except XPI.DoesNotExist:
        print(Fore.RED + 'File does not exist.')
        quit(1)
    except XPI.BadZipfile:
        print(Fore.RED + 'XPI cannot be unzipped.')
        quit(1)
    except XPI.BadXPIfile:
        print(Fore.RED + 'XPI is not properly configured.')
        quit(1)
    else:
        print(Fore.CYAN + 'Found: {}'.format(xpi.release_name))

        if not click.confirm(Style.RESET_ALL + 'Is this correct?'):
            print(Fore.RED + 'Release could not be auto-generated.')
            quit(1)

        session = boto3.Session(profile_name=profile)
        s3 = session.resource('s3')
        bucket = s3.Bucket(BUCKET_NAME)

        exists = False
        for obj in bucket.objects.filter(Prefix=PREFIX):
            if obj.key == xpi.get_ftp_path(PREFIX):
                exists = True

        uploaded = False
        if exists:
            tmpdir = tempfile.mkdtemp()
            download_path = os.path.join(tmpdir, xpi.file_name)
            bucket.download_file(xpi.get_ftp_path(PREFIX), download_path)
            uploaded_xpi = XPI(download_path)

            if uploaded_xpi.sha512sum == xpi.sha512sum:
                print(Fore.GREEN + 'XPI already uploaded.')
                uploaded = True
            else:
                print(Fore.YELLOW + 'XPI with matching filename already uploaded.')

        if not uploaded:
            if exists and not click.confirm(Style.RESET_ALL + 'Would you like to replace it?'):
                print(Fore.RED + 'Aborting.')
                quit(1)
            with open(xpi.path, 'rb') as data:
                bucket.put_object(Key=xpi.get_ftp_path(PREFIX), Body=data)
            print(Fore.GREEN + 'XPI uploaded successfully.')

        json_path = 'releases/{}.json'.format(xpi.release_name)

        if os.path.exists(json_path):
            print(Fore.YELLOW + 'Release JSON file already exists.')
            if not click.confirm(Style.RESET_ALL + 'Replace existing release JSON file?'):
                print(Fore.RED + 'Aborting.')
                quit(1)

        print(Style.RESET_ALL + 'Saving to: {}{}'.format(Style.BRIGHT, json_path))

        os.makedirs('releases', exist_ok=True)
        with open(json_path, 'w') as f:
            f.write(json.dumps(xpi.generate_release_data(BASE_URL, PREFIX), indent=2,
                               sort_keys=True))

    quit(0)


@cli.command()
@click.argument('releases', nargs=-1)
def mksuperblob(releases):
    names = []

    for release in releases:
        with open(release, 'r') as f:
            release_data = json.loads(f.read())
        names.append(release_data['name'])

    if not len(names):
        print(Fore.RED + 'No releases specified.')
        quit(1)

    sb_name = 'SystemAddons-{}-Superblob'.format('-'.join(names))
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

    quit(0)


if __name__ == '__main__':
    cli()
