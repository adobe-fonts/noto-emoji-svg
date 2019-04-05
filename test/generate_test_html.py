# Copyright © 2019 Adobe, Inc.
# Author: Miguel Sousa
"""
Generates an HTML page for testing emoji characters.
"""
import io
import os
import sys
from shutil import copyfile


FILE_PREFIX = 'emoji_u'

TEST_DIR = os.path.abspath(os.path.dirname(__file__))
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
    http://unicode.org/Public/emoji/12.0/emoji-test.txt)
    and returns a list of code points.
    """
    with io.open(EMOJI_TEST_FILE, encoding='utf-8') as fp:
        lines = fp.read().splitlines()

    cdpts_list = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        codepoints = line.split(';')[0].strip().split()
        cdpts_list.append(codepoints)
    return cdpts_list


def main(args=None):
    cdpts_list = parse_emoji_test_file()
    copyfile(TEST_HEADER_FILE, TEST_FILE)

    for i, cps in enumerate(cdpts_list, 1):
        # XXX ignore variation sequences for now
        if 'FE0F' in cps:
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
