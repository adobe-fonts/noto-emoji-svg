# Copyright © 2019 Adobe, Inc.
# Author: Miguel Sousa
"""
Generates an HTML page for testing emoji characters.
"""
import argparse
import io
import os
import sys
from shutil import copyfile

REG_IND_LETTR = ('1F1E6 1F1E7 1F1E8 1F1E9 1F1EA 1F1EB 1F1EC 1F1ED '
                 '1F1EE 1F1EF 1F1F0 1F1F1 1F1F2 1F1F3 1F1F4 1F1F5 '
                 '1F1F6 1F1F7 1F1F8 1F1F9 1F1FA 1F1FB 1F1FC 1F1FD '
                 '1F1FE 1F1FF').split()

MIN_ITEMS_PPAGE = 50
DFLT_ITEMS_PPAGE = 500

FILE_PREFIX = 'emoji_u'

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
EMOJI_TEST_FILE = os.path.join(TEST_DIR, 'emoji-test.txt')
TEST_HEADER_FILE = os.path.join(TEST_DIR, 'test_header.html')
TEST_FILE_NAME = 'test{}.html'

TABLE_ROW = """<tr>
    <th scope="row">#{}<br>{}</th>
    <td class="font_fallback">{}</td>
    <td><img src="png/{}.png"></td>
    <td><img src="svg/{}.svg"></td>
    <!-- <td class="font_emoji_color">{}</td> -->
    <td><img src="svg_bw/{}.svg"></td>
    <td class="font_emoji_bw">{}</td>
</tr>
"""
LINK_ROW = """<tr>
    <th colspan="7" class="bold_center">
        Continues at <a href="{0}">{0}</a>
    </th>
</tr>
"""
TEST_FOOTER = """</table></div></body></html>"""


def append_to_file(fpath, data):
    with io.open(fpath, 'a', encoding='utf-8') as fp:
        fp.write(data)


def make_path(file_num):
    num = '' if file_num == 1 else file_num
    return os.path.join(TEST_DIR, '..', TEST_FILE_NAME.format(num))


def parse_emoji_test_file():
    """
    Parses Unicode's 'emoji-test.txt' file (available from
    http://unicode.org/Public/emoji/M.m/ where 'M.m' is the version number)
    and returns a list of code points.
    """
    with io.open(EMOJI_TEST_FILE, encoding='utf-8') as fp:
        lines = fp.read().splitlines()

    cdpts_list = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        codepoints, status = line.split(';')
        if 'unqualified' in status or 'non-fully-qualified' in status:
            continue
        cdpts_list.append(codepoints.strip().split())
    return cdpts_list


def _positive_int(int_str):
    try:
        num_items = int(int_str)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "'{}' is not an integer.".format(int_str))
    if num_items < MIN_ITEMS_PPAGE:
        raise argparse.ArgumentTypeError('Number of items per page must be '
                                         '{} or more.'.format(MIN_ITEMS_PPAGE))
    return num_items


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-p',
        '--paginate',
        help=('breaks up the resulting HTML into multiple files. The default '
              'number of items per page is {} and the minimum is {}.'
              ''.format(DFLT_ITEMS_PPAGE, MIN_ITEMS_PPAGE)),
        metavar='INTEGER or blank',
        type=_positive_int,
        default=0,
        nargs='?',
    )
    opts = parser.parse_args(args)

    if opts.paginate == 0:
        # option was NOT used
        items_ppage = None
    elif opts.paginate is None:
        # option was used but it was NOT followed by an integer
        items_ppage = DFLT_ITEMS_PPAGE
    else:
        items_ppage = opts.paginate

    # collect the list of codepoints
    cdpts_list = parse_emoji_test_file()

    html_file_num = 1
    start_file = True

    for i, cps in enumerate(cdpts_list, 1):
        # XXX skip country flags for now
        if cps[0] in REG_IND_LETTR:
            continue
        cps_html = ''.join('&#x{};'.format(cp) for cp in cps)
        # filenames have no 'FE0F' component
        cps_filename = [cp for cp in cps if cp != 'FE0F']
        filename = FILE_PREFIX + '_'.join(cps_filename).lower()
        html = TABLE_ROW.format(i, ' '.join(cps), cps_html, filename,
                                filename, cps_html, filename, cps_html)
        if start_file:
            test_file_path = make_path(html_file_num)
            copyfile(TEST_HEADER_FILE, test_file_path)
            start_file = False

        append_to_file(test_file_path, html)

        if items_ppage and (i % items_ppage == 0):
            # flip the start_file switch
            start_file = True
            # increment the file number
            html_file_num += 1
            # add link to the next file
            append_to_file(test_file_path, LINK_ROW.format(
                TEST_FILE_NAME.format(html_file_num)))
            # finish the current file
            append_to_file(test_file_path, TEST_FOOTER)

    append_to_file(test_file_path, TEST_FOOTER)


if __name__ == "__main__":
    sys.exit(main())
