# --------------------------------------------------
#    Imports
# --------------------------------------------------
import configparser
import importlib
import inspect
import logging
import os
import shutil
import traceback
import uuid


# --------------------------------------------------
#    Globals
# --------------------------------------------------
DEFAULT_SAVE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'_static/files/')


# --------------------------------------------------
#    Config File
# --------------------------------------------------
"""
# Example conf file
[FileGeneration]
save_file_path = /usr/local/generated_files
url_prefix = https://www.example.com/generated_files

[ModuleInjection]
module_list = testmod.xx

[Logging]
log_level = INFO
"""

CONFIG_FILE = '/etc/chatgpt_awesome_actions_datamodule.conf'
CONFIG = None
if os.path.isfile(CONFIG_FILE):
    CONFIG = configparser.ConfigParser()
    CONFIG.read(CONFIG_FILE)


# --------------------------------------------------
#    Cached Config Vars
# --------------------------------------------------
LOG_LEVEL  = 'INFO' if CONFIG is None else CONFIG.get('Logging', 'log_level', fallback='INFO')
MODULE_LIST_STR = '' if CONFIG is None else CONFIG.get('ModuleInjection', 'module_list', fallback='')
SAVE_FILE_DIR = DEFAULT_SAVE_FILE_PATH if CONFIG is None else CONFIG.get('FileGeneration', 'save_file_path', fallback=DEFAULT_SAVE_FILE_PATH)
URL_PREFIX = 'http://localhost' if CONFIG is None else CONFIG.get('FileGeneration', 'url_prefix', fallback='http://localhost')


# --------------------------------------------------
#    Logging
# --------------------------------------------------
logging.basicConfig(level=LOG_LEVEL)


# --------------------------------------------------
#    Load functions from modules
# --------------------------------------------------
INJECTED_GLOBALS = {}
for m in MODULE_LIST_STR.split(','):
    try:
        module = importlib.import_module(m)
        logging.info(f'{m} was succesfully imported')

        for name in dir(module):
            if not name.startswith("_"):  # Skip private and built-in attributes
                attr = getattr(module, name)
                if inspect.isfunction(attr):  # Ensure it's a function
                    logging.info(f'    Injecting function {name} into globals')
                    INJECTED_GLOBALS[name] = attr
    except:
        logging.exception(f'Error trying to import {m}')


# --------------------------------------------------
#    Functions
# --------------------------------------------------
def echo(msg: str) -> dict:
    """
    Echoes back a message as a test.

    Parameters:
        msg (str): The message to be returned.

    Returns:
        dict: A dictionary containing the response with:
            - 'body' (str): The echoed message.
            - 'content-type' (str): The MIME type of the response.
    """
    return {'body': msg, 'content-type': 'text/plain'}


def _exec_python_code(code: str) -> dict:
    """
    Executes the provided Python code and returns the result.

    Parameters:
        code (str): The Python code to execute. The code should define `__retval__` as the result.

    Returns:
        dict: A dictionary containing the response with:
            - 'body' (str): The result of the executed code. If an error occurs, this contains the traceback.
            - 'content-type' (str): The MIME type of the response, either 'text/plain' for success or 'text/error' for errors.
    """
    print(code)

    globals_dict = INJECTED_GLOBALS.copy()

    # local_vars = {}
    try:
        exec(code, globals_dict)
        data = str(globals_dict['__retval__'])
        return {'body': data, 'content-type': 'text/plain'}

    except:
        print(traceback.format_exc())
        return {'body': traceback.format_exc(), 'content-type': 'text/error'}


def exec_python_code_return_string(code: str) -> dict:
    """
    Executes the provided Python code and returns the result as a string.

    Parameters:
        code (str): The Python code to execute. The code must assign a value to `__retval__`
                    for this function to return meaningful data.

    Returns:
        dict: A dictionary containing the response with:
            - 'body' (str): The result of the executed code, extracted from `__retval__`.
            - 'content-type' (str): The MIME type of the response, either 'text/plain' for success
                                    or 'text/error' if an exception occurs.
    """
    return _exec_python_code(code)


def exec_python_code_return_URL(code: str) -> dict:
    """
    Executes Python code that generates a file in the `/tmp/` directory and returns a secure,
    obfuscated URL to access it.

    Parameters:
        code (str): The Python code to execute. The code must define the absolute file path in the
                    `__retval__` variable, pointing to a file saved in the `/tmp/` directory.

    Returns:
        dict: A dictionary containing the response with:
            - 'body' (str): A secure, opaque URL pointing to the file's contents. The file is not
                            directly accessible from `/tmp/` and can only be retrieved via the provided URL.
            - 'content-type' (str): The MIME type of the response, set to 'text/uri-list' for success.

    Raises:
        Exception: If the generated file is not located in the `/tmp/` directory or does not exist.

    Security Notice:
        The generated file in `/tmp/` is not directly accessible. Instead, it is copied to a
        controlled storage location with an obfuscated filename, and only the returned URL can
        be used to access it.
    """
    retval = _exec_python_code(code)
    if retval['content-type'] == 'text/error':
        return retval

    src_filepath = retval['body']
    src_filepath = os.path.abspath(src_filepath)
    if not src_filepath.startswith('/tmp/'):
        raise Exception('Error!  Generated file must be in /tmp/ directory')

    if not os.path.exists(src_filepath):
        raise Exception('Error!  File not found!')

    src_filename = os.path.basename(src_filepath)
    dst_filename = f"{uuid.uuid4().hex}_{src_filename}"
    dst_filepath = os.path.join(SAVE_FILE_DIR, dst_filename)
    shutil.copy(src_filepath, dst_filepath)

    url = os.path.join(URL_PREFIX, dst_filename)
    print(f'\bGenerated URL: {url}')
    return {'body': url, 'content-type': 'text/uri-list'}
