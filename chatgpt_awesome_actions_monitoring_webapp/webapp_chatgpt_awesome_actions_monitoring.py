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

        if ('target' in params) and ('value' in params):
            target = params.get('target', ['?'])[0]
            value = params.get('value', ['?'])[0]

            if target == '#code':
                value = python_to_html(value)
            # else:
            #     value = html.escape(value)

            s = datetime.now(pytz.timezone("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S %Z")
            for bjsc in get_broadcast_jsclients('/'):
                bjsc['#last_update_time'].html = s
                try:
                    bjsc[target].html = value
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
