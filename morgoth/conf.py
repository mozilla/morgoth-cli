import os

import yaml

from colorama import Fore, Style


if not os.path.exists('.morgoth.yml'):
    print(Fore.RED + 'Configuration file is missing.')
    print(Style.RESET_ALL)
    exit(1)

with open('.morgoth.yml', 'r') as f:
    settings = yaml.safe_load(f)
