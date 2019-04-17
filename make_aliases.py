# Copyright © 2019 Adobe, Inc.
# Author: Miguel Sousa
"""
Creates aliases of SVG files in the same directory.
"""
import argparse
import io
import logging
import os
import sys


FILE_PREFIX = 'emoji_u'

log = logging.getLogger('make_aliases')


def make_aliases(aliases_list, in_dir):
    os.chdir(in_dir)

    for src_name, dst_name in aliases_list:
        src_filename = '{}{}.svg'.format(FILE_PREFIX, src_name)
        dst_filename = '{}{}.svg'.format(FILE_PREFIX, dst_name)

        if not os.path.exists(src_filename):
            log.warning("File named '{}' not found in '{}'".format(
                src_filename, in_dir))
            continue

        if os.path.exists(dst_filename):
            os.remove(dst_filename)

        os.symlink(src_filename, dst_filename)


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


def _validate_dir_path(path_str):
    valid_path = os.path.abspath(os.path.realpath(path_str))
    if not os.path.isdir(valid_path):
        raise argparse.ArgumentTypeError(
            "{} is not a valid directory path.".format(path_str))
    return _normalize_path(path_str)


def _validate_file_path(path_str):
    valid_path = os.path.abspath(os.path.realpath(path_str))
    if not os.path.isfile(valid_path):
        raise argparse.ArgumentTypeError(
            "{} is not a valid file path.".format(path_str))
    return _normalize_path(path_str)


def _normalize_path(path_str):
    return os.path.normpath(path_str)


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
        type=_validate_file_path,
    )
    parser.add_argument(
        'in_dir',
        help='input directory containing SVG files',
        metavar='DIR',
        type=_validate_dir_path,
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
