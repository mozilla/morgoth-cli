import base64
import os


BASE_PATH = os.getcwd()
MORGOTH_PATH = os.path.join(BASE_PATH, '.morgoth')
ENVIRONMENT_PATH = os.path.join(MORGOTH_PATH, 'env')
CONFIG_PATH = os.path.join(MORGOTH_PATH, 'config')

STATUS_5H17 = base64.b64decode(
    b'CiAgICAgKCAgICkKICAoICAgKSAoCiAgICkgXyAgICkKIC'
    b'AgICggXF8KICBfKF9cIFwpX18KIChfX19fXF9fXykpCg==').decode()
