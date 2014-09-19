'''Allows executing and formatting ReQL queries and JSON responses'''
from __future__ import print_function

import json
import datetime
import traceback
import os
import sys
import termios
import tty
import re
import functools
import base64

from pygments import highlight
from pygments.lexers import JsonLexer, PythonLexer
from pygments.formatters import Terminal256Formatter
from pygments.styles import STYLE_MAP

import rethinkdb as r


class ReQLExecution(object):
    def __init__(self, querystring, files, connection, output):
        self.querystring = querystring
        self.conn = connection
        self.output = output
        self.results = None
        self._query = None
        self.environment = files
        self.environment.update({
            'r': r,
            '__builtins__': {
                'True': True,
                'False': False,
                'None': None,
            }
        })

    @property
    def query(self):
        '''The compiled query from the input query string'''
        if self._query is None:
            self._query = r.expr(eval(self.querystring, self.environment))
        return self._query

    def __call__(self):
        '''Executes the query and sends it to the output'''
        try:
            self.results = self.query.run(
                self.conn,
                binary_format=self.output.binary_format,
                time_format=self.output.time_format)
            self.output(self.results, self.query)
        except r.RqlError as e:
            self.output.error(e)
        except NameError as ne:
            self.output.error(ne.message)
        except SyntaxError as se:
            exc_list = traceback.format_exception_only(type(se), se)[1:]
            exc_list[0] = self.output.python_format(exc_list[0])
            self.output.error('\n', ''.join(exc_list))
        except AttributeError as ae:
            self.output.error(ae.message)
        except KeyboardInterrupt:
            pass


def filename_to_var(filename):
    '''Transforms a filename into a usable variable name'''
    return re.sub(r'\W', '_', os.path.basename(filename).split('.', 1)[0])


def binary_patch(func):
    '''decorator to monkey patch the json encoder so it doesn't
    accidentally try to print out binaries (which may have null bytes
    in them)'''

    real_encoder = json.encoder.encode_basestring

    def reql_encode_basestring(s):
        if isinstance(s, r.ast.RqlBinary):
            return '"' + base64.b64encode(s) + '"'
        else:
            return real_encoder(s)

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        orig = json.encoder.encode_basestring
        json.encoder.encode_basestring = reql_encode_basestring
        try:
            return func(*args, **kwargs)
        finally:
            json.encoder.encode_basestring = orig

    return _wrapper


class DateJSONEncoder(json.JSONEncoder):
    '''Will format datetimes as iso8601'''
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()


class Output(object):
    '''Centralizes output behavior'''

    input_stream = sys.stdin
    output_stream = sys.stdout
    error_stream = sys.stderr

    @staticmethod
    def make(format, style, pagesize):
        '''Factory method to create the appropriate output'''
        is_atty = os.isatty(sys.stdout.fileno())
        if format == 'color' or format == 'auto' and is_atty:
            return ColorOutput(style, pagesize)
        elif format == 'newline' or format == 'auto' and not is_atty:
            return NewlineOutput()
        elif format == 'array':
            return ArrayOutput()
        else:
            raise Exception('{} {} {} is illegal!'.format(
                format, style, pagesize))

    @binary_patch
    def format(self, doc):
        '''Dumps a json value according to the current format'''
        return json.dumps(
            doc,
            indent=None if self.compact else 4,
            sort_keys=not self.compact,
            separators=(',', ':') if self.compact else (', ', ': '),
            cls=json.JSONEncoder if self.compact else DateJSONEncoder,
            ensure_ascii=False,
        )

    def python_format(self, obj):
        return obj

    def print(self, *args, **kwargs):
        '''Print a value to stdout'''
        kwargs.setdefault('file', self.output_stream)
        print(*args, **kwargs)

    def fprint(self, value, **kwargs):
        '''Format string equivalent of printf'''
        kwargs.setdefault('file', self.output_stream)
        print(self.format(value), **kwargs)

    def error(self, value, *args, **kwargs):
        '''Print a value to stderr'''
        kwargs.setdefault('file', self.error_stream)
        print(value, *args, **kwargs)


    def getch(self):
        """getch() -> key character

        Read a single keypress from stdin and return the resulting character.
        Nothing is echoed to the console. This call will block if a keypress
        is not already available, but will not wait for Enter to be pressed.

        If the pressed key was a modifier key, nothing will be detected; if
        it were a special function key, it may return the first character of
        of an escape sequence, leaving additional characters in the buffer.

        From http://code.activestate.com/recipes/577977-get-single-keypress/
        """
        fd = self.input_stream.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = self.input_stream.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class ColorOutput(Output):
    '''User friendly output'''

    time_format = 'native'
    binary_format = 'native'
    compact = False

    def __init__(self, style, pagesize):
        self.style = style if style in STYLE_MAP else 'monokai'
        self.pagesize = pagesize

    def format(self, doc):
        doc = super(ColorOutput, self).format(doc)
        return highlight(
            doc, JsonLexer(), Terminal256Formatter(style=self.style))

    def primitive_array(self, docs):
        '''Whether a document is an array of primitives'''
        primitives = (int, float, bool, basestring)
        return isinstance(docs, list) and \
            all(isinstance(x, primitives) for x in docs)

    def python_format(self, obj):
        '''Colorizes python strings'''
        return highlight(str(obj),
                         PythonLexer(),
                         Terminal256Formatter(style=self.style))

    def __call__(self, docs, query):
        if isinstance(docs, dict) and 'first_error' in docs:
            # Detect errors that don't raise exceptions
            self.error(docs['first_error'].replace('\t', '  '))
            return
        if self.primitive_array(docs):
            self.compact = True
        if isinstance(docs, (dict, int, float, bool, basestring)) or \
           self.primitive_array(docs):
            # Print small things directly
            self.fprint(docs)
            self.print('Ran:\n', self.python_format(query))
            return
        i = 0  # in case no results
        for i, doc in enumerate(docs, start=1):
            self.fprint(doc)
            if i % self.pagesize == 0:
                self.print('Running:', self.python_format(query))
                self.print('[%s] Hit any key to continue (or q to quit)...' % i)
                char = self.getch()
                if char.lower() == 'q':
                    raise SystemExit()
        self.print('Total docs:', i)
        self.print('Ran:\n', self.python_format(query))


class NewlineOutput(Output):
    '''Newline separated compact json document output'''

    time_format = 'raw'
    binary_format = 'raw'
    compact = True

    def __call__(self, docs, _):
        if isinstance(docs, dict):
            self.fprint(docs)
        else:
            for doc in docs:
                self.fprint(doc)


class ArrayOutput(Output):
    '''JSON array output. Can be parsed by any JSON interpreter'''

    time_format = 'raw'
    binary_format = 'raw'
    compact = True

    def print(self, *args, **kwargs):
        super(ArrayOutput, self).print(*args, **kwargs)
        self.output_stream.flush()

    def __call__(self, docs, _):
        if isinstance(docs, dict):
            self.fprint(docs)
        elif isinstance(docs, r.Cursor):
            first = True
            self.print('[', end='')
            try:
                for doc in docs:
                    if not first:
                        self.print(',', sep='', end='')
                    else:
                        first = False
                    self.fprint(doc, sep='', end='')
            finally:
                self.print(']')
        else:
            self.fprint(docs)
