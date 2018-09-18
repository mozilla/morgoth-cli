import base64
import os

HOME_DIR = os.path.expanduser('~')
CONFIG_PATH = os.path.join(HOME_DIR, '.morgoth_config')
GPG_HOMEDIR_DEFAULT = os.path.join(HOME_DIR, '.gnupg')

STATUS_5H17 = base64.b64decode(
    b'CiAgICAgKCAgICkKICAoICAgKSAoCiAgICkgXyAgICkKIC'
    b'AgICggXF8KICBfKF9cIFwpX18KIChfX19fXF9fXykpCg==').decode()
