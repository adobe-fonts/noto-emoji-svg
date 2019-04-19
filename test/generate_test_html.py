# Copyright © 2019 Adobe, Inc.
# Author: Miguel Sousa
"""
Generates an HTML page for testing emoji characters.
"""
import io
import os
import sys
from shutil import copyfile

REG_IND_LETTR = ('1F1E6 1F1E7 1F1E8 1F1E9 1F1EA 1F1EB 1F1EC 1F1ED '
                 '1F1EE 1F1EF 1F1F0 1F1F1 1F1F2 1F1F3 1F1F4 1F1F5 '
                 '1F1F6 1F1F7 1F1F8 1F1F9 1F1FA 1F1FB 1F1FC 1F1FD '
                 '1F1FE 1F1FF').split()

FILE_PREFIX = 'emoji_u'

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
EMOJI_TEST_FILE = os.path.join(TEST_DIR, 'emoji-test.txt')
TEST_HEADER_FILE = os.path.join(TEST_DIR, 'test_header.html')
TEST_FILE = os.path.join(TEST_DIR, '../test.html')

TABLE_ROW = """<tr>
    <th scope="row">#{}<br>{}</th>
    <td class="font_fallback">{}</td>
    <td><img src="svg/{}.svg"></td>
    <!-- <td class="font_emoji_color">{}</td> -->
    <td><img src="svg_bw/{}.svg"></td>
    <td class="font_emoji_bw">{}</td>
</tr>
"""
TEST_FOOTER = """</table></div></body></html>"""


def append_to_file(fpath, data):
    with io.open(fpath, 'a', encoding='utf-8') as fp:
        fp.write(data)


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


def main(args=None):
    cdpts_list = parse_emoji_test_file()
    copyfile(TEST_HEADER_FILE, TEST_FILE)

    for i, cps in enumerate(cdpts_list, 1):
        # XXX skip country flags for now
        if cps[0] in REG_IND_LETTR:
            continue
        cps_html = ''.join(['&#x{};'.format(cp) for cp in cps])
        filename = FILE_PREFIX + '_'.join(cps).lower()
        html = TABLE_ROW.format(i, ' '.join(cps), cps_html,
                                filename, cps_html,
                                filename, cps_html)
        append_to_file(TEST_FILE, html)
    append_to_file(TEST_FILE, TEST_FOOTER)


if __name__ == "__main__":
    sys.exit(main())
