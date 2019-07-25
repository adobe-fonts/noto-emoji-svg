# Copyright © 2019 Adobe, Inc.
# Author: Miguel Sousa
"""
Generates a simple text file for testing emoji characters.
"""
import argparse
import os
import sys

from generate_test_html import (TEST_DIR, append_to_file, REG_IND_LETTR,
                                parse_emoji_test_file, TAG_LAT_LETTR)

TEST_FILE_NAME = 'test.txt'


def positive_int(int_str):
    try:
        num_items = int(int_str)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "'{}' is not an integer.".format(int_str))
    if num_items < 1:
        raise argparse.ArgumentTypeError('Number of emoji per line must be 1 '
                                         'or more.')
    return num_items


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-e',
        '--emoji-per-line',
        help=('split the single line of emoji characters/sequences by '
              'introducing line breaks'),
        metavar='INTEGER',
        type=positive_int,
    )
    parser.add_argument(
        '-s',
        '--space',
        help=('add space character between emoji characters/sequences'),
        action='store_true'
    )
    opts = parser.parse_args(args)

    # collect the list of codepoints
    cdpts_list = parse_emoji_test_file()

    # start a new file (avoids appending to an existing file)
    test_file_path = os.path.join(TEST_DIR, '..', TEST_FILE_NAME)
    open(test_file_path, 'w').close()

    # begin the file with the BOM and use utf-16-le encoding
    # (to make Adobe Illustrator happy)
    append_to_file(test_file_path, '\uFEFF', 'utf-16-le')

    emoji_list = []
    for i, cps in enumerate(cdpts_list, 1):
        # XXX skip country and regional flags for now
        if len(cps) > 1 and cps[1] in (REG_IND_LETTR + TAG_LAT_LETTR):
            continue
        emoji = ''.join(chr(int(cp, 16)) for cp in cps)
        emoji_list.append(emoji)

    if opts.space:
        space = ' '
    else:
        space = ''

    if opts.emoji_per_line:
        emoji_stream = ''
        for i, emoji_group in enumerate(emoji_list, 1):
            emoji_sep = '\r' if i % opts.emoji_per_line == 0 else space
            emoji_stream += '{}{}'.format(emoji_group, emoji_sep)
    else:
        emoji_stream = space.join(emoji_list)

    append_to_file(test_file_path, emoji_stream, 'utf-16-le')


if __name__ == "__main__":
    sys.exit(main())
