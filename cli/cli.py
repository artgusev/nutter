import os

__version__ = '0.1.36'

BUILD_NUMBER_ENV_VAR = 'NUTTER_BUILD_NUMBER'

def get_cli_version():
    build_number = os.environ.get(BUILD_NUMBER_ENV_VAR)
    if build_number:
        return '{}.{}'.format(__version__, build_number)
    return __version__
