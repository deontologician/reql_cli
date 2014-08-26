'''Allows executing and formatting ReQL queries and JSON responses'''
from __future__ import print_function

import json
import datetime
import traceback
import os
import sys
import termios
import tty

import pygments
from pygments import highlight
from pygments.lexers import JsonLexer, PythonLexer
from pygments.formatters import Terminal256Formatter
from pygments.styles import STYLE_MAP

import rethinkdb as r

BEING_PIPED = not os.isatty(sys.stdout.fileno())

class DateJSONEncoder(json.JSONEncoder):
    '''Will format datetimes as iso8601'''
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

def json_format(value, style='monokai'):
    '''Formats a json value in a user friendly way'''
    try:
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        output_string = json.dumps(
            value,
            indent=None if BEING_PIPED else 4,
            sort_keys=not BEING_PIPED,
            separators=(',', ':') if BEING_PIPED else (', ', ': '),
            cls=DateJSONEncoder)
    except Exception as e:
        return repr(value)
    if BEING_PIPED:
        return output_string
    else:
        return highlight(
            output_string, JsonLexer(), Terminal256Formatter(style=style))


def python_format(output_string, style='monokai'):
    '''Colorizes python strings'''
    return highlight(
        output_string, PythonLexer(), Terminal256Formatter(style=style))

def evaluate(querystring):
    return r.expr(eval(querystring, {
            'r': r,
            '__builtins__': {
                'True': True,
                'False': False,
                'None': None,
            }
        }))

def execute(host, port, db, querystring, pagesize):
    '''Executes a query with the given connection arguments'''
    try:
        conn = r.connect(host=host, port=port, db=db)
        try:
            query = evaluate(querystring)
        except NameError:
            # Assume it's just a string if the variable isn't defined
            query = evaluate(repr(querystring))
        result = query.run(conn)

        if isinstance(result, dict) and 'first_error' in result:
            print(result['first_error'].replace('\t', '  '))
        elif isinstance(result, (dict, int, float, bool, basestring)):
            print(json_format(result))
            if not BEING_PIPED:
                print('Ran:\n', python_format(str(query)))
        else:
            for i, doc in enumerate(result, start=1):
                print(json_format(doc))
                if not BEING_PIPED and i % pagesize == 0:
                    print('[{}] Hit any key to continue (or q to quit)...'.format(i))
                    char = getch()
                    if char.lower() == 'q':
                        raise SystemExit()

            if not BEING_PIPED:
                print('Total docs:', i)
                print('Ran:\n', python_format(querystring))

    except r.RqlError as e:
        print(e)
    except NameError as ne:
        print(ne.args, ne.message)
    except SyntaxError as se:
        exc_list = traceback.format_exception_only(type(se), se)[1:]
        exc_list[0] = python_format(exc_list[0])
        print('\n', ''.join(exc_list))


def getch():
    """getch() -> key character

    Read a single keypress from stdin and return the resulting character.
    Nothing is echoed to the console. This call will block if a keypress
    is not already available, but will not wait for Enter to be pressed.

    If the pressed key was a modifier key, nothing will be detected; if
    it were a special function key, it may return the first character of
    of an escape sequence, leaving additional characters in the buffer.

    From http://code.activestate.com/recipes/577977-get-single-keypress/
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch
