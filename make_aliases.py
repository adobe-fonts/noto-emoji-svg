# Copyright © 2019 Adobe, Inc.
# Author: Miguel Sousa
"""
Creates aliases of SVG or PNG files in the same directory.
"""
import argparse
import io
import logging
import os
import sys

from make_bw_font import validate_dir_path, validate_file_path


FILE_PREFIX = 'emoji_u'
FILE_EXTENSIONS = ('svg', 'png')

log = logging.getLogger('make_aliases')


def sniff_file_extension(src_name):
    for ext in FILE_EXTENSIONS:
        src_filename = '{}{}.{}'.format(FILE_PREFIX, src_name, ext)
        if os.path.exists(src_filename):
            return src_filename, ext
    # no file was found
    return None, None


def make_aliases(aliases_list, in_dir):
    os.chdir(in_dir)

    for src_name, dst_name in aliases_list:
        src_filename, ext = sniff_file_extension(src_name)
        if not src_filename:
            log.warning("File named '{}{}' not found in '{}'".format(
                FILE_PREFIX, src_name, in_dir))
            continue

        dst_filename = '{}{}.{}'.format(FILE_PREFIX, dst_name, ext)
        if os.path.exists(dst_filename):
            os.remove(dst_filename)

        try:
            os.symlink(src_filename, dst_filename)
        except OSError as err:
            if err.args == ('symbolic link privilege not held',):
                log.error('On Windows this script must be run in Admin mode.')
            else:
                log.error('Failure while trying to create alias/symlink.')
            return 1


def parse_emoji_aliases_file(file_path):
    """
    Parses an emoji aliases text file.
    Returns a list of tuples in the form ('src_name', 'dst_name').
    """
    with io.open(file_path, encoding='utf-8') as fp:
        lines = fp.read().splitlines()

    aliases_list = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # strip in-line comments
        comment_idx = line.find('#')
        if comment_idx > 0:
            line = line[:comment_idx].strip()
        aliases_list.append(tuple(line.split(';')))
    return aliases_list


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-v',
        '--verbose',
        help='verbose mode. Use -vv for debug mode',
        action='count',
        default=0
    )
    parser.add_argument(
        'in_file',
        help='text file containing a listing of the aliases',
        metavar='FILE',
        type=validate_file_path,
    )
    parser.add_argument(
        'in_dir',
        help='input directory containing SVG files',
        metavar='DIR',
        type=validate_dir_path,
    )
    opts = parser.parse_args(args)

    if not opts.verbose:
        level = "WARNING"
    elif opts.verbose == 1:
        level = "INFO"
    else:
        level = "DEBUG"
    logging.basicConfig(level=level)

    aliases_list = parse_emoji_aliases_file(opts.in_file)
    make_aliases(aliases_list, opts.in_dir)


if __name__ == "__main__":
    sys.exit(main())
