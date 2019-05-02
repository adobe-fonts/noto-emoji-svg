# Copyright © 2019 Adobe, Inc.
# Author: Miguel Sousa
"""
Generates a simple text file for testing emoji characters.
"""
import os
import sys

from generate_test_html import (TEST_DIR, append_to_file, REG_IND_LETTR,
                                parse_emoji_test_file)

TEST_FILE_NAME = 'test.txt'


def main(args=None):
    # collect the list of codepoints
    cdpts_list = parse_emoji_test_file()

    emoji_list = []
    for i, cps in enumerate(cdpts_list, 1):
        # XXX skip country flags for now
        if cps[0] in REG_IND_LETTR:
            continue
        emoji = ''.join(chr(int(cp, 16)) for cp in cps)
        emoji_list.append(emoji)

    test_file_path = os.path.join(TEST_DIR, '..', TEST_FILE_NAME)
    append_to_file(test_file_path, ' '.join(emoji_list))


if __name__ == "__main__":
    sys.exit(main())
