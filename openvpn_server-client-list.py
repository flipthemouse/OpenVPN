#! /usr/bin/env python3
# -*- coding: utf-8; py-indent-offset: 4 -*-
# See  https://github.com/Linuxfabrik/monitoring-plugins/tree/main/check-plugins/openvpn-client-list
# One python file that outputs all connected openVPN clients
# Data are taken from /var/log/openvpn/openvpn-status.log
# Ensure that your server.conf has included line: "status  /var/log/openvpn/openvpn-status.log" !

import os
import operator
import argparse 
import sys
import collections
import operator
import sys
from traceback import format_exc

string_types = str
integer_types = int
class_types = type
text_type = str
binary_type = bytes

STATE_OK = 0
STATE_WARN = 1
STATE_CRIT = 2
STATE_UNKNOWN = 3
DEFAULT_WARN = None
DEFAULT_CRIT = None
DESCRIPTION = 'Prints a list of all clients connected to the OpenVPN Server'
DEFAULT_FILENAME = '/var/log/openvpn/openvpn-status.log'

def csv(arg):
    # Returns a list from a csv input argument.
    return [x.strip() for x in arg.split(',')]

def oao(msg, state=STATE_OK, perfdata='', always_ok=False):
    # Over and Out (OaO)
    # Print the stripped plugin message. If perfdata is given, attach it by |
    # and print it stripped. Exit with state, or with STATE_OK (0) if always_ok is set to True.

    if perfdata:
        print(msg.strip() + ' ! ' + perfdata.strip())
    else:
        print(msg.strip())
    if always_ok:
        sys.exit(0)
    sys.exit(state)

def get_state(value, warn, crit, _operator='ge'):
    # Returns the STATE by comparing valu` to the given thresholds using
    # a comparison _operator. warn and crit threshold may also be None.
    # make sure to use float comparison
    value = float(value)
    if _operator == 'ge':
        if crit is not None:
            if value >= float(crit):
                return STATE_CRIT
        if warn is not None:
            if value >= float(warn):
                return STATE_WARN
        return STATE_OK

    if _operator == 'gt':
        if crit is not None:
            if value > float(crit):
                return STATE_CRIT
        if warn is not None:
            if value > float(warn):
                return STATE_WARN
        return STATE_OK

    if _operator == 'le':
        if crit is not None:
            if value <= float(crit):
                return STATE_CRIT
        if warn is not None:
            if value <= float(warn):
                return STATE_WARN
        return STATE_OK

    if _operator == 'lt':
        if crit is not None:
            if value < float(crit):
                return STATE_CRIT
        if warn is not None:
            if value < float(warn):
                return STATE_WARN
        return STATE_OK

    if _operator == 'eq':
        if crit is not None:
            if value == float(crit):
                return STATE_CRIT
        if warn is not None:
            if value == float(warn):
                return STATE_WARN
        return STATE_OK

    if _operator == 'ne':
        if crit is not None:
            if value != float(crit):
                return STATE_CRIT
        if warn is not None:
            if value != float(warn):
                return STATE_WARN
        return STATE_OK

    if _operator == 'range':
        if crit is not None:
            if not coe(match_range(value, crit)):
                return STATE_CRIT
        if warn is not None:
            if not coe(match_range(value, warn)):
                return STATE_WARN
        return STATE_OK

    return STATE_UNKNOWN

def get_perfdata(label, value, uom=None, warn=None, crit=None, _min=None, _max=None):
    # Returns 'label'=value[UOM];[warn];[crit];[min];[max]
    msg = " {} = {}".format(label, value)
    if uom is not None:
        msg += uom
    msg += ';'
    if warn is not None:
        msg += str(warn)
    msg += ';'
    if crit is not None:
        msg += str(crit)
    msg += ';'
    if _min is not None:
        msg += str(_min)
    msg += ';'
    if _max is not None:
        msg += str(_max)
    msg += ' '
    return msg

def cu():
    # See you (cu)
    # Prints a Stacktrace (replacing "<" and ">" to be printable in Web-GUIs), and exits with STATE_UNKNOWN.
    print(format_exc().replace("<", "'").replace(">", "'"))
    sys.exit(STATE_UNKNOWN)

def read_file(filename):
    # Reads a file.
    try:
        with open(filename, 'r') as f:
            data = f.read()
    except IOError as e:
        return (False, 'I/O error "{}" while opening or reading {}'.format(e.strerror, filename))
    except:
        return (False, 'Unknown error opening or reading {}'.format(filename))
    return (True, data)

def test(args):
    # Returns the content of two files as well as the provided return code. The first file stands
    # for STDOUT, the second for STDERR. The function can be used to enable unit tests.
    # >>> test('path/to/stdout.txt', 'path/to/stderr.txt', 128)
    if args[0] and os.path.isfile(args[0]):
        success, stdout = read_file(args[0])
    else:
        stdout = args[0]
    if args[1] and os.path.isfile(args[1]):
        success, stderr = read_file(args[1])
    else:
        stderr = args[1]
    if args[2] == '':
        retc = 0
    else:
        retc = int(args[2])

    return stdout, stderr, retc

def pluralize(noun, value, suffix='s'):
    # Returns a plural suffix if the value is not 1. By default, 's' is used as
    # the suffix.See https://kite.com/python/docs/django.template.defaultfilters.pluralize

    if ',' in suffix:
        singular, plural = suffix.split(',')
    else:
        singular, plural = '', suffix
    if int(value) == 1:
        return noun + singular
    return noun + plural

def get_table(data, cols, header=None, strip=True, sort_by_key=None, sort_order_reverse=False):
    # Takes a list of dictionaries, formats the data, and returns the formatted data as a text table.
    # See https://www.calazan.com/python-function-for-displaying-a-list-of-dictionaries-in-table-format/
    
    if not data:
        return ''

    # Sort the data if a sort key is specified (default sort order is ascending)
    if sort_by_key:
        data = sorted(data,
                      key=operator.itemgetter(sort_by_key),
                      reverse=sort_order_reverse)

    # If header is not empty, create a list of dictionary from the cols and the header and
    # insert it before first row of data
    if header:
        header = dict(zip(cols, header))
        data.insert(0, header)

    # prepare data: decode from (mostly) UTF-8 to Unicode, optionally strip values and get
    # the maximum length per column
    column_widths = collections.OrderedDict()
    for idx, row in enumerate(data):
        for col in cols:
            try:
                if strip:
                    data[idx][col] = str(row[col]).strip()
                else:
                    data[idx][col] = str(row[col])
            except:
                return 'Unknown column "{}"'.format(col)
            # get the maximum length
            try:
                column_widths[col] = max(column_widths[col], len(data[idx][col]))
            except:
                column_widths[col] = len(data[idx][col])

    if header:
        # Get the length of each column and create a '---' divider based on that length
        header_divider = []
        for col, width in column_widths.items():
            header_divider.append('-' * width)

        # Insert the header divider below the header row
        header_divider = dict(zip(cols, header_divider))
        data.insert(1, header_divider)

    # create the output
    table = ''
    cnt = 0
    for row in data:
        tmp = ''
        for col, width in column_widths.items():
            if cnt != 1:
                tmp += '{:<{}} ! '.format(row[col], width)
            else:
                # header row
                tmp += '{:<{}}-+-'.format(row[col], width)
        cnt += 1
        table += tmp[:-2] + '\n'

    return table

def coe(result, state=STATE_UNKNOWN):
    # Continue or Exit (CoE)
    # This is useful if calling complex library functions in your checks
    # main() function. Don't use this in functions.

    if result[0]:
        # success
        return result[1]
    print(result[1])
    sys.exit(state)

def match_range(value, spec):
    """
    # You should not delete comment as it affects next function : def parse_args()
    # Decides if `value` is inside/outside the threshold spec.
    # See https://github.com/mpounsett/nagiosplugin/blob/master/nagiosplugin/range.py
    """

def parse_args():
    """Parse command line arguments using argparse.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument(
        '-c', '--critical',
        help='Set the critical threshold for the number of connected clients. Default: %(default)s',
        dest='CRIT',
        type=int,
        default=DEFAULT_CRIT,
    )

    parser.add_argument(
        '--filename',
        help='Set the path of the log filename. Default: %(default)s',
        dest='FILENAME',
        type=str,
        default=DEFAULT_FILENAME,
    )

    parser.add_argument(
        '--test',
        help='For unit tests. Needs "path-to-stdout-file,path-to-stderr-file,expected-retc".',
        dest='TEST',
        type=csv,
    )

    parser.add_argument(
        '-w', '--warning',
        help='Set the warning threshold for the number of connected clients. Default: %(default)s',
        dest='WARN',
        type=int,
        default=DEFAULT_WARN,
    )

    return parser.parse_args()


def main():
    # parse the command line, exit with UNKNOWN if it fails
    try:
        args = parse_args()
    except SystemExit:
        sys.exit(STATE_UNKNOWN)

    # fetch data
    if args.TEST is None:
        try:
            with open(args.FILENAME, 'r') as file:
                counter = 0
                table = []
                for line in file:
                    if line.startswith('CLIENT_LIST'):
                        counter += 1
                        line = line.split(',')
                        table.append({
                            'name': line[1],
                            'ext_ip': line[2].split(':')[0],
                            'int_ip': line[3],
                            'connection_time': line[7],
                        })
        except IOError:
            oao('Failed to read file {}.'.format(args.FILENAME), STATE_UNKNOWN)
    else:
        # do not call the command, put in test data
        stdout, stderr, retc = test(args.TEST)
        oao('TODO')

    state = get_state(counter, args.WARN, args.CRIT)
    perfdata = get_perfdata('clients', counter, None, args.WARN, args.CRIT, 0, None)

    msg = '{} {} connected to OpenVPN Server.\n\n'.format(
        counter,
        pluralize('user', counter)
    )

    msg += get_table(
        table,
        ['name', 'ext_ip', 'int_ip', 'connection_time'],
        header=['Common Name', 'External IP', 'Internal IP', 'Connected since'],
    )

    # over and out
    oao(msg, state, perfdata)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        cu()
