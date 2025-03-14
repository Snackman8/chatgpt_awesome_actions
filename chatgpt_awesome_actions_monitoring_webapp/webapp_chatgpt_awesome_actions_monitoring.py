import argparse
import logging
import html
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import pytz
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

from pylinkjs.PyLinkJS import run_pylinkjs_app, get_broadcast_jsclients
from collections import OrderedDict

class FIFODict(OrderedDict):
    def __init__(self, max_size=5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_size = max_size

    def __setitem__(self, key, value):
        if len(self) >= self.max_size:
            self.popitem(last=False)  # Remove the oldest (FIFO)
        super().__setitem__(key, value)

    def __contains__(self, key):
        """Allows checking if a key exists using 'key in fifo_dict'"""
        return key in self.keys()


row_values = FIFODict(max_size=10)

def python_to_html(code):
    """Convert Python code to syntax-highlighted HTML while preserving line breaks."""
    formatter = HtmlFormatter(style="colorful", nowrap=True)  # Keep formatting inside div
    highlighted_code = highlight(code, PythonLexer(), formatter)

    # Get CSS styles for Pygments
    css = HtmlFormatter(style="colorful").get_style_defs('.highlight')

    # Wrap output in <pre> to preserve line breaks
    return f'<style>{css}</style><pre class="highlight">{highlighted_code}</pre>'


def ready(jsc, *args):
    """ called when a webpage creates a new connection the first time on load """
    print('Ready', args)


def reconnect(jsc, *args):
    """ called when a webpage automatically reconnects a broken connection """
    print('Reconnect', args)


def handle_404(path, uri, *args):
    # handle URLS that do not have html pages
    if path == 'update_monitor':

        parsed_url = urlparse(uri)
        params = parse_qs(parsed_url.query)

        if ('uid' in params) and ('target' in params) and ('value' in params):
            uid = params.get('uid', ['?'])[0]
            target = params.get('target', ['?'])[0]
            value = params.get('value', ['?'])[0]
            value_time = params.get('time', 0)[0]

            if target == 'code':
                value = python_to_html(value)

            s = datetime.now(pytz.timezone("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S %Z")
            value = f'<div style="background-color: yellow">{s} - {uid.partition(":")[0]}</div>{value}'

            if uid not in row_values:
                row_values[uid] = {'code': {'time': 0, 's': ''}, 'retval': {'time': 0, 's': ''}}
            if float(value_time) > row_values[uid][target]['time']:
                row_values[uid][target] = {'time': float(value_time), 's': value}

            # build the table
            html = '<table>'
            for _, value in list(row_values.items())[::-1]:
                html += f'<tr><td>{value["code"]["s"]}</td><td>{value["retval"]["s"]}</td></tr>'
            html += '<table>'

            for bjsc in get_broadcast_jsclients('/'):
                try:
                    bjsc['#code_retval'].html = html
                except Exception as e:
                    logging.exception(e)
        else:
            logging.info('Missing target or value')

    return ('OK', 'text/plain', 200)


# --------------------------------------------------
#    Main
# --------------------------------------------------
if __name__ == '__main__':
    # setup the logger
    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s %(message)s')

    # handle the --port argument
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=False, default=8300)
    args = vars(parser.parse_args())

    # run the app
    run_pylinkjs_app(default_html='webapp_chatgpt_awesome_actions_monitoring.html',
                     html_dir=os.path.dirname(__file__),
                     on_404=handle_404,
                     internal_polling_interval=0.025,
                     port=args['port'])
