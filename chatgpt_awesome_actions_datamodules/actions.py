# --------------------------------------------------
#    Imports
# --------------------------------------------------
import configparser
import json
import os
import pickle
import shutil
import sqlite3
import sys
import traceback
import uuid
import pandas as pd


# --------------------------------------------------
#    CONFIG FILE
# --------------------------------------------------
CONFIG_FILE = '/etc/datamodule_gpt_action_servicenow.conf'
CONFIG = None
if os.path.isfile(CONFIG_FILE):
    CONFIG = configparser.ConfigParser()
    CONFIG.read(CONFIG_FILE)


# --------------------------------------------------
#    CACHED CONFIG VARS
# --------------------------------------------------
DB_PATH = '' if CONFIG is None else CONFIG.get('LocalDB', 'db_path', fallback='')


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



def _execute_servicenow_sql(sql):
    """
Run SQL on service now data.  Results are returned as dataframe

Table: incidents
Columns: number, opened_at, resolved_at, category, subcategory, state, impact, urgency, priority, close_code, short_description, location, assigned_to

Params:
    sql - (str) SQL query to run on the filtered data.
    """
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn)


# def _exec_python_code(code, filename=None):
#     """
# Executes the provided Python code, returns value, and optionally saves binary data to a file.  Set __retval__ inside the code for returned data.
#
# Returns a dict with 'body' (If filename is given, returns a URL to the returned data, otherwise returns the returned data.
#
# Params:
#     code - (str) The Python code to execute. The code should define `__retval__` as the result.
#     filename - (str, optional) Name of the file to save the data. A unique prefix will be added.
#     """
#     print(f'Filename: {filename}')
#     print(code)
#
#     # execute_servicenow_sql function takes a single parameter sql, executes the sql, and returns back a dataframe
#     globals_dict = {"execute_servicenow_sql": _execute_servicenow_sql}
#
#     local_vars = {}
#     try:
#         exec(code, globals_dict)
#         data = globals_dict['__retval__']
#         if filename:
#             filename = f"{uuid.uuid4().hex}_{filename}"
#
#             with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'_static/files/{filename}'), 'wb') as f:
#                 try:
#                     f.write(data)
#                 except:
#                     f.write(json.dumps(data).encode('utf-8'))
#
#             url = f'https://testapi.projectredline.com/gpt_action_servicenow/files/{filename}'
#
#             return {'body': url, 'content-type': 'text/uri-list'}
#         else:
#             try:
#                 return {'body': data, 'content-type': 'text/plain'}
#             except:
#                 return {'body': f.write(json.dumps(data).encode('utf-8')), 'content-type': 'text/plain'}
#
#     except Exception as e:
#         print(traceback.format_exc())
#         return {'body': traceback.format_exc(), 'content-type': 'text/error'}


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

    globals_dict = {}

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
    dst_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'_static/files/{dst_filename}')
    shutil.copy(src_filepath, dst_filepath)

    url = f'https://testapi.projectredline.com/gpt_action_servicenow/files/{dst_filename}'
    print(url)
    return {'body': url, 'content-type': 'text/uri-list'}




