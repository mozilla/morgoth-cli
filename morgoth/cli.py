import os
import json
import tempfile

from hashlib import sha256

import boto3
import click

from colorama import Fore, Style

from morgoth import CONFIG_PATH, ENVIRONMENT_PATH, STATUS_5H17
from morgoth.environment import Environment
from morgoth.settings import GPGImproperlyConfigured, settings
from morgoth.utils import output, validate_environment
from morgoth.xpi import XPI


@click.group()
def cli():
    pass


@cli.command()
@click.option('--environment', '-e', default=None)
@click.option('--username', '-u', default=None)
@click.pass_context
def init(ctx, environment, username):
    """Initialize a Morgoth repository."""
    curr_env = None
    if os.path.exists(ENVIRONMENT_PATH):
        output('A repo has already been initialized in this directory.')
        curr_env = Environment.from_file(ENVIRONMENT_PATH)

    # Prompt for a password if a username is provided
    password = None
    if username:
        password = click.prompt('Password', hide_input=True)

    if environment:
        environment = Environment(environment, username=username, password=password)
        is_valid, message = validate_environment(environment)
        if not is_valid:
            output(message)
            exit(1)

    while not environment:
        url = click.prompt('Environment URL')
        environment = Environment(url, username=username, password=password)
        is_valid, message = validate_environment(environment)
        if not is_valid:
            output(message)
            environment = None

    if curr_env and environment != curr_env:
        if not click.confirm('Would you like to replace the existing environment?'):
            exit(1)
    elif curr_env:
        output('Environment was unchanged.')

    environment.save(ENVIRONMENT_PATH)

    if username:
        settings.path = CONFIG_PATH

        if click.confirm('Do you want to save your username?'):
            ctx.invoke(config, key='username', value=username)

        if click.confirm('Do you want to save your password?'):
            ctx.invoke(config, key='password', value=password)


@cli.command()
@click.option('--username', '-u', default=None)
@click.pass_context
def auth(ctx, username):
    """Update authentication settings."""
    if not username:
        username = click.prompt('Username')

    password = None
    while not password:
        password = click.prompt('Password', hide_input=True)
        confirm_password = click.prompt('Confirm Password', hide_input=True)

        if password != confirm_password:
            output('Passwords did not match. Try again.')
            password = None

    ctx.invoke(config, key='username', value=username)
    ctx.invoke(config, key='password', value=password)


@cli.command()
@click.option('--delete', '-d', is_flag=True)
@click.option('--list', '-l', is_flag=True)
@click.argument('key', default='')
@click.argument('value', default='')
def config(key, value, delete, list):
    """Get or set a configuration value."""
    if list:
        for section in settings.config:
            for option in settings.config[section]:
                key = '{}.{}'.format(section, option)
                output('{} = {}'.format(key, settings.get(key)))
    elif delete:
        try:
            settings.delete(key)
        except KeyError:
            output('Setting does not exist.')
            exit(1)
    elif value == '':
        if settings.get(key):
            output(settings.get(key))
            exit(0)
    elif key:
        try:
            settings.set(key, value)
        except GPGImproperlyConfigured:
            output('GPG settings improperly configured.')
            exit(1)

    settings.save()


@cli.command()
@click.option('--verbose', '-v', is_flag=True)
def status(verbose):
    """Show the current status."""
    if verbose:
        output(STATUS_5H17)


@cli.group()
def make():
    """Make a new object."""
    pass


@make.command('release')
@click.option('--profile', default=settings.get('aws.profile'))
@click.argument('xpi_file')
def make_release(xpi_file, profile):
    """Make a new release from an XPI file."""
    prefix = settings.get('aws.prefix')

    try:
        xpi = XPI(xpi_file)
    except XPI.DoesNotExist:
        output('File does not exist.', Fore.RED)
        exit(1)
    except XPI.BadZipfile:
        output('XPI cannot be unzipped.', Fore.RED)
        exit(1)
    except XPI.BadXPIfile:
        output('XPI is not properly configured.', Fore.RED)
        exit(1)
    else:
        output('Found: {}'.format(xpi.release_name), Fore.CYAN)

        if not click.confirm('Is this correct?'):
            output('Release could not be auto-generated.', Fore.RED)
            exit(1)

        session = boto3.Session(profile_name=profile)
        s3 = session.resource('s3')
        bucket = s3.Bucket(settings.get('aws.bucket_name'))

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
                output('XPI already uploaded.', Fore.GREEN)
                uploaded = True
            else:
                output('XPI with matching filename already uploaded.', Fore.YELLOW)

        if not uploaded:
            if exists and not click.confirm('Would you like to replace it?'):
                output('Aborting.', Fore.RED)
                exit(1)
            with open(xpi.path, 'rb') as data:
                bucket.put_object(Key=xpi.get_ftp_path(prefix), Body=data)
                output('XPI uploaded successfully.', Fore.GREEN)

        json_path = 'releases/{}.json'.format(xpi.release_name)

        if os.path.exists(json_path):
            output('Release JSON file already exists.', Fore.YELLOW)
            if not click.confirm('Replace existing release JSON file?'):
                output('Aborting.', Fore.RED)
                exit(1)

        output('Saving to: {}{}'.format(Style.BRIGHT, json_path))

        os.makedirs('releases', exist_ok=True)
        with open(json_path, 'w') as f:
            f.write(json.dumps(
                xpi.generate_release_data(settings.get('aws.base_url'), prefix),
                indent=2, sort_keys=True))

    output('')


@make.command('superblob')
@click.argument('releases', nargs=-1)
def make_superblob(releases):
    """Make a new superblob from releases."""
    names = []

    for release in releases:
        with open(release, 'r') as f:
            release_data = json.loads(f.read())
        short_name = release_data['name'].split('@')[0]
        for k in release_data['addons']:
            if k.startswith(short_name):
                version = release_data['addons'][k]['version']
        names.append(release_data['name'])

    if not len(names):
        output('No releases specified.', Fore.RED)
        exit(1)

    names.sort()
    names_string = '-'.join(names)
    names_hash = sha256(names_string.encode()).hexdigest()

    sb_name = 'Superblob-{}'.format(names_hash)
    sb_data = {
      'blobs': names,
      'name': sb_name,
      'schema_version': 4000
    }

    sb_path = 'releases/superblobs/{}.json'.format(sb_name)
    os.makedirs('releases/superblobs', exist_ok=True)
    with open(sb_path, 'w') as f:
        f.write(json.dumps(sb_data, indent=2, sort_keys=True))

    output('Saving to: {}{}'.format(Style.BRIGHT, sb_path))

    output('')
