# --------------------------------------------------
#    Imports
# --------------------------------------------------
import configparser
import importlib
import inspect
import logging
import os
import psutil
import shutil
import signal
import socket
import subprocess
import sys
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

[WebApps]
url_prefix = http://localhost

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
WEBAPP_URL_PREFIX = 'http://localhost' if CONFIG is None else CONFIG.get('WebApps', 'url_prefix', fallback='http://localhost')


# --------------------------------------------------
#    Logging
# --------------------------------------------------
logging.basicConfig(level=LOG_LEVEL)


# --------------------------------------------------
#    Load functions from modules
# --------------------------------------------------
INJECTED_GLOBALS = {}
if MODULE_LIST_STR.strip() != '':
    for m in MODULE_LIST_STR.strip().split(','):
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
def _cleanup_old_webapps():
    # Look for processes containing "/app.py" and "--port"
    logging.info(f"Cleaning up old webapps")
    matching_processes = []
    for process in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        try:
            cmdline = process.info["cmdline"]
            if (
                cmdline and
                any("/app.py" in arg for arg in cmdline) and
                any("--port" in arg for arg in cmdline) and
                cmdline[0] == sys.executable
            ):
                matching_processes.append(process.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass  # Process no longer exists or permission denied

    # Kill matching processes
    for proc in matching_processes:
        try:
            pid = proc["pid"]
            logging.info(f"Killing PID {pid}: {' '.join(proc['cmdline'])}")
            os.kill(pid, signal.SIGTERM)  # Graceful termination
        except (psutil.NoSuchProcess, PermissionError):
            logging.info(f"Failed to kill PID {pid}")

    logging.info("Done.")

# force cleanup
#_cleanup_old_webapps()


# --------------------------------------------------
#    Functions
# --------------------------------------------------
def _convert_public_to_save_path(public_url: str) -> str:
    """
    Converts a publicly accessible URL back to the corresponding file path in SAVE_FILE_DIR.

    Parameters:
        public_url (str): The public URL.

    Returns:
        str: The absolute path of the file in SAVE_FILE_DIR.
    """
    if not public_url.startswith(URL_PREFIX):
        raise Exception("Error! URL does not match expected prefix.")

    # Extract UUID-prefixed filename from the public URL
    filename = os.path.basename(public_url)

    # Reconstruct the full file path inside SAVE_FILE_DIR
    file_path = os.path.join(SAVE_FILE_DIR, filename)

    if not os.path.exists(file_path):
        raise Exception("Error! File does not exist in SAVE_FILE_DIR.")

    return file_path


def _convert_tmp_to_save_path(src_filepath: str) -> dict:
    """
    Converts a file path inside /tmp/ to a publicly accessible file path.

    Parameters:
        src_filepath (str): The absolute path of the file inside the /tmp/ directory.

    Returns:
        tuple: A tuple containing:
            - dst_filepath (str): The new file path in the save directory.
            - dst_filename (str): The new filename with a unique identifier.

    Raises:
        Exception: If the file is not inside /tmp/ or does not exist.
    """
    # Ensure the path is inside /tmp/
    src_filepath = os.path.abspath(src_filepath)
    if not src_filepath.startswith('/tmp/'):
        raise Exception('Error!  Generated file must be in /tmp/ directory')

    # Ensure the file exists
    if not os.path.exists(src_filepath):
        raise Exception('Error!  File not found!')

    # Generate a unique filename
    src_filename = os.path.basename(src_filepath)
    dst_filename = f"{uuid.uuid4().hex}_{src_filename}"
    dst_filepath = os.path.join(SAVE_FILE_DIR, dst_filename)

    # Construct the public URL
    return dst_filepath, dst_filename


def _find_free_port(start=9000, end=10000):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port

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
    logging.info('==================================================')
    logging.info(f'echo')
    logging.info('==================================================')
    logging.info(f'\n{msg}\n')
    d = {'body': msg, 'content-type': 'text/plain'}
    logging.info('\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n')
    logging.info(f'\n{d}\n')
    logging.info('\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n')
    return d


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
    logging.info('==================================================')
    logging.info(f'exec_python_code_return_string')
    logging.info('==================================================')
    logging.info(f'\n{code}\n\n')
    d = _exec_python_code(code)
    logging.info('\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n')
    logging.info(f'\n{d}\n')
    logging.info('\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n')
    return d


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
    logging.info('==================================================')
    logging.info(f'exec_python_code_return_URL')
    logging.info('==================================================')
    logging.info(f'\n{code}\n\n')

    retval = _exec_python_code(code)
    if retval['content-type'] == 'text/error':
        return retval

    src_filepath = retval['body']

    dst_filepath, dst_filename = _convert_tmp_to_public(src_filepath)
    logging.info(f'Copying {src_filepath} to {dst_filepath}.  filename={dst_filename}')
    #
    #
    # src_filepath = os.path.abspath(src_filepath)
    # if not src_filepath.startswith('/tmp/'):
    #     raise Exception('Error!  Generated file must be in /tmp/ directory')
    #
    # if not os.path.exists(src_filepath):
    #     raise Exception('Error!  File not found!')
    #
    # src_filename = os.path.basename(src_filepath)
    # dst_filename = f"{uuid.uuid4().hex}_{src_filename}"
    # dst_filepath = os.path.join(SAVE_FILE_DIR, dst_filename)
    if os.path.isfile(src_filepath):
        shutil.copy(src_filepath, dst_filepath)
    else:
        shutil.copytree(src_filepath, dst_filepath)

    url = os.path.join(URL_PREFIX, dst_filename)
    d = {'body': url, 'content-type': 'text/uri-list'}
    logging.info('\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n')
    logging.info(f'\n{d}\n')
    logging.info('\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n')
    return d



def exec_pylinkjs_app(url: str) -> dict:
    """
    Launches a pylinkjs application from the specified URL in an isolated environment and
    returns a secure, dynamically assigned URL to access it.

    Parameters:
        url (str): The external URL pointing to the pylinkjs application source code. The function
                   maps this to an internal file location where the app is stored.

    Returns:
        dict: A dictionary containing the response with:
            - 'body' (str): A unique URL where the pylinkjs application can be accessed.
            - 'content-type' (str): The MIME type of the response, set to 'text/uri-list' for success.

    Raises:
        Exception: If the application directory cannot be determined or the application fails to start.

    Security Notice:
        The pylinkjs application runs in an isolated environment. The assigned network port is
        dynamically allocated to avoid conflicts, and the application remains accessible only
        through the returned URL.
    """
    logging.info('==================================================')
    logging.info(f'exec_pylinkjs_app')
    logging.info('==================================================')
    logging.info(f'\n{url}\n\n')

    # Extract internal file location from the given URL
    _, _, webapp_dir = url.rpartition('/files/')
    webapp_dir = os.path.join(SAVE_FILE_DIR, webapp_dir)

    # Define the expected pylinkjs entry point
    webapp_app_path = os.path.join(webapp_dir, 'app.py')

    # Find an available network port within the specified range
    free_port = _find_free_port(start=9000, end=10000)

    # Launch the pylinkjs application in the background
    subprocess.Popen(
        [sys.executable, webapp_app_path, '--port', str(free_port)],
        close_fds=True,
        cwd=webapp_dir
    )

    # generate the redirect file
    redirect_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="refresh" content="0; url={WEBAPP_URL_PREFIX}:{free_port}">
            <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0">
            <meta http-equiv="Pragma" content="no-cache">
            <meta http-equiv="Expires" content="0">
            <title>Redirecting...</title>
        </head>
        <body>
            <p>If you are not redirected, <a href="{WEBAPP_URL_PREFIX}:{free_port}">click here</a>.</p>
        </body>
        </html>
    """
    save_path = _convert_public_to_save_path(url)
    dst_filepath = os.path.join(save_path, 'redirect.html')
    with open(dst_filepath, 'w') as f:
        f.write(redirect_html)

    # Return the URL where the application is accessible
    d = {'body': f"{os.path.join(url, 'redirect.html')}", 'content-type': 'text/uri-list'}
    logging.info('\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n')
    logging.info(f'\n{d}\n')
    logging.info('\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n')
    return d
    