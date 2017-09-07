from urllib.error import HTTPError

from colorama import Style


def output(str, *styles):
    print(Style.RESET_ALL, end='')
    if styles:
        print(*styles, end='')
    print(str, end='')
    print(Style.RESET_ALL)


def validate_environment(env, **kwargs):
    try:
        is_valid = env.validate(**kwargs)
    except HTTPError:
        return False, 'Could not authenticate.'
    return is_valid, '' if is_valid else 'Invalid environment.'
