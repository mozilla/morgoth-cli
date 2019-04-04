import os
import json
import tempfile

from datetime import datetime
from hashlib import sha256

import boto3
import click

from colorama import Fore, Style
from requests.exceptions import HTTPError, Timeout

from morgoth import CONFIG_PATH, STATUS_5H17
from morgoth.environment import Environment
from morgoth.settings import settings
from morgoth.utils import output
from morgoth.xpi import XPI


DEFAULT_BALROG_URL = 'https://aus4-admin.mozilla.org/'
DEFAULT_AWS_BASE_URL = 'https://ftp.mozilla.org/'
DEFAULT_AWS_BUCKET_NAME = 'net-mozaws-prod-delivery-archive'
DEFAULT_AWS_PREFIX = 'pub/system-addons/'


def get_validated_environment(**kwargs):
    environment = Environment(
        kwargs.get('url', settings.get('balrog_url')),
        bearer_token=kwargs.get('bearer_token', settings.get('bearer_token')))

    try:
        environment.validate()
    except Timeout:
        output('Timeout while attempting to connect. Check VPN.', Fore.RED)
        exit(1)
    except HTTPError as err:
        if err.response.status_code == 401:
            output('Invalid bearer token.', Fore.RED)
            if kwargs.get('verbose'):
                output('Error from server:')
                output(json.dumps(err.response.json(), indent=2))
            exit(1)
        raise

    return environment


@click.group()
def cli():
    pass


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize Morgoth."""
    url = click.prompt('Balrog URL', settings.get('balrog_url', DEFAULT_BALROG_URL))

    # Create a settings file
    settings.path = CONFIG_PATH

    ctx.invoke(config, key='balrog_url', value=url)


@cli.command()
@click.option('--bearer', '-b', default=None)
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def auth(ctx, bearer, verbose):
    """Update authentication settings."""
    if not bearer:
        bearer = click.prompt('Bearer Token')

    output('Attempting to validate Balrog credentials...', Fore.BLUE)
    get_validated_environment(bearer_token=bearer, verbose=verbose)

    ctx.invoke(config, key='bearer_token', value=bearer)


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
        settings.set(key, value)

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
@click.option('--bearer', '-b', default=None)
@click.option('--profile', default=settings.get('aws.profile'))
@click.option('--verbose', '-v', is_flag=True)
@click.argument('xpi_file')
def make_release(xpi_file, bearer, profile, verbose):
    """Make a new release from an XPI file."""
    prefix = settings.get('aws.prefix', DEFAULT_AWS_PREFIX)

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
        bucket = s3.Bucket(settings.get('aws.bucket_name', DEFAULT_AWS_BUCKET_NAME))

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

        release_data = xpi.generate_release_data(
            settings.get('aws.base_url', DEFAULT_AWS_BASE_URL), prefix)

        if click.confirm('Upload release to Balrog?'):
            extra_kw = {}
            if bearer:
                extra_kw.update({"bearer_token": bearer})
            environment = get_validated_environment(verbose=verbose, **extra_kw)

            try:
                environment.request('releases', data={
                'blob': json.dumps(release_data),
                'name': xpi.release_name,
                'product': 'SystemAddons',
                'csrf_token': environment.csrf(),
            })
            except HTTPError as err:
                output(f'An error occured: HTTP {err.response.status_code}', Fore.RED)
                if verbose:
                    output('Request headers:')
                    output(json.dumps(dict(err.request.headers), indent=2))
                    output('Request body:')
                    output(json.dumps(json.loads(err.request.body.decode()), indent=2))
                    output('Error from server:')
                    output(json.dumps(err.response.json(), indent=2))
                exit(1)

            output('Uploaded: {}{}'.format(Style.BRIGHT, xpi.release_name))
        elif click.confirm('Save release to file?'):
            json_path = 'releases/{}.json'.format(xpi.release_name)

            if os.path.exists(json_path):
                output('Release JSON file already exists.', Fore.YELLOW)
                if not click.confirm('Replace existing release JSON file?'):
                    output('Aborting.', Fore.RED)
                    exit(1)

            output('Saving to: {}{}'.format(Style.BRIGHT, json_path))

            os.makedirs('releases', exist_ok=True)
            with open(json_path, 'w') as f:
                f.write(json.dumps(release_data, indent=2, sort_keys=True))
        else:
            output(json.dumps(release_data, indent=2, sort_keys=True))

    output('')


@make.command('superblob')
@click.option('--bearer', '-b', default=None)
@click.option('--verbose', '-v', is_flag=True)
@click.argument('releases', nargs=-1)
def make_superblob(releases, bearer, verbose):
    """Make a new superblob from releases."""
    names = []

    for release in releases:
        if os.path.exists(release):
            with open(release, 'r') as f:
                release_data = json.loads(f.read())
            names.append(release_data['name'])
        else:
            names.append(release)

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

    if click.confirm('Upload release to Balrog?'):
        extra_kw = {}
        if bearer:
            extra_kw.update({"bearer_token": bearer})
        environment = get_validated_environment(verbose=verbose, **extra_kw)

        try:
            environment.request('releases', data={
                'blob': json.dumps(sb_data),
                'name': sb_name,
                'product': 'SystemAddons',
                'csrf_token': environment.csrf(),
            })
        except HTTPError as err:
            output(f'An error occured: HTTP {err.response.status_code}', Fore.RED)
            if verbose:
                output('Request headers:')
                output(json.dumps(dict(err.request.headers), indent=2))
                output('Request body:')
                output(json.dumps(json.loads(err.request.body.decode()), indent=2))
                output('Error from server:')
                output(json.dumps(err.response.json(), indent=2))
            exit(1)

        output('Uploaded: {}{}'.format(Style.BRIGHT, sb_name))
    elif click.confirm('Save release to file?'):
        sb_path = 'releases/superblobs/{}.json'.format(sb_name)
        os.makedirs('releases/superblobs', exist_ok=True)
        with open(sb_path, 'w') as f:
            f.write(json.dumps(sb_data, indent=2, sort_keys=True))

        output('Saving to: {}{}'.format(Style.BRIGHT, sb_path))
    else:
        output(json.dumps(sb_data, indent=2, sort_keys=True))

    output('')


@cli.group()
def modify():
    """Modify an object"""
    pass


@modify.command('rules')
@click.argument('rule_ids', nargs=-1)
@click.option('--add', '-a', help='Add a release to the rules.')
@click.option('--bearer', '-b', default=None)
@click.option('--remove', '-r', help='Remove a release from the rules.')
@click.option('--verbose', '-v', is_flag=True)
def modify_rules(rule_ids, add, bearer, remove, verbose):
    """Modify rules."""
    extra_kw = {}
    if bearer:
        extra_kw.update({"bearer_token": bearer})
    environment = get_validated_environment(verbose=verbose)

    # Fetch a list of all releases
    data = environment.request('releases').json()
    releases = data.get('releases', [])
    release_names = [r.get('name') for r in releases if r.get('product') == 'SystemAddons']

    # Validate release to be added
    if add and add not in release_names:
        output('The release you are trying to add does not exist.', Fore.RED)
        exit(1)

    for rule_id in rule_ids:
        # Fetch existing rule
        rule = environment.fetch(f'rules/{rule_id}')

        # Fetch release for rule
        superblob = environment.fetch(f'releases/{rule["mapping"]}')

        # Construct new superblob with release
        if add and add not in superblob['blobs']:
            superblob['blobs'].append(add)
        if remove and remove in superblob['blobs']:
            superblob['blobs'].remove(remove)
        superblob['blobs'].sort()
        name_hash = sha256('-'.join(superblob['blobs']).encode()).hexdigest()
        superblob['name'] = f'Superblob-{name_hash}'

        # Check if the superblob already exists
        create_release = superblob['name'] not in release_names

        # Check if the mapping is already set
        update_mapping = rule['mapping'] != superblob['name']

        # Confirm changes
        if create_release:
            output(f'Will add new release {superblob["name"]}:')
            output('{}\n'.format(json.dumps(superblob, indent=2)), Style.BRIGHT)

        if update_mapping:
            output(f'Will modify: {Style.BRIGHT}Rule {rule_id} '
                   f'(channel: {rule["channel"]}, version: {rule["version"]})')
            output(f'From mapping: {Style.BRIGHT}{rule["mapping"]}')
            output(f'To mapping: {Style.BRIGHT}{superblob["name"]}\n')

        if update_mapping or create_release:
            if not click.confirm('Apply these changes?'):
                output('Aborted!')
                exit(1)
        else:
            output(f'Skipping rule {rule_id}, nothing to change.', Fore.YELLOW)
            continue

        csrf_token = environment.csrf()

        # Create release
        if create_release:
            try:
                environment.request('releases', data={
                    'blob': json.dumps(superblob),
                    'name': superblob['name'],
                    'product': 'SystemAddons',
                    'csrf_token': csrf_token,
                })
            except HTTPError as err:
                output('Unable to create release', Fore.RED)
                output(f'An error occured: HTTP {err.response.status_code}', Fore.RED)
                if verbose:
                    output('Request headers:')
                    output(json.dumps(dict(err.request.headers), indent=2))
                    output('Request body:')
                    output(json.dumps(json.loads(err.request.body.decode()), indent=2))
                    output('Error from server:')
                    output(json.dumps(err.response.json(), indent=2))
                exit(1)
            release_names.append(superblob['name'])

        # Save new mapping to rule
        if update_mapping:
            ts_now = int(datetime.now().timestamp() * 1000)
            rule['mapping'] = superblob['name']
            try:
                environment.request('scheduled_changes/rules', data={
                    **rule,
                    'when': ts_now + (5 * 1000),  # in five seconds
                    'change_type': 'update',
                    'csrf_token': csrf_token,
                })
            except HTTPError as err:
                response_data = err.response.json()
                output('Unable to update rule!', Fore.RED)
                if 'data' in response_data:
                    output(response_data.get('data'), Fore.RED)
                exit(1)

    output('Done!', Fore.GREEN)
