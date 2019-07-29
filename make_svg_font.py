# Copyright © 2019 Adobe, Inc.
# Author: Miguel Sousa
"""
Adds an SVG table to an OpenType font.
"""
import argparse
import glob
import io
import logging
import os
import re
import sys

from ast import literal_eval
from decimal import Decimal

from fontTools.ttLib import TTFont, TTLibError, newTable

from make_bw_font import (
    FILE_PREFIX, VENDOR, glyph_name_is_valid, get_trimmed_glyph_name,
    validate_dir_path, validate_file_path, validate_revision_number,
    SVG_SIZE, UPM, EMOJI_SIZE, EMOJI_H_ADV, ASCENT)

FAMILY_NAME = 'Noto Color Emoji SVG'
FULL_NAME = FAMILY_NAME
PS_NAME = 'NotoColorEmoji-SVG'


def norm_float(value):
    """
    Converts a float (whose decimal part is zero) to integer
    """
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


VIEWBOX_X_SHIFT = norm_float(
    (EMOJI_SIZE - EMOJI_H_ADV) / EMOJI_SIZE * SVG_SIZE / 2)
VIEWBOX_Y_SHIFT = norm_float(SVG_SIZE * ASCENT / EMOJI_SIZE)
VIEWBOX_SCALE = norm_float(UPM / EMOJI_SIZE)


RE_XMLHEADER = re.compile(r"<\?xml .*\?>")
RE_SVGID = re.compile(r"<svg[^>]+?(id=\".*?\").+?>", re.DOTALL)
RE_ENABLEBKGD = re.compile(r"( enable-background=[\"|\'][new\d, ]+[\"|\'])")
RE_SPACEBTWEEN = re.compile(r">\s+<", re.MULTILINE)
# The value of the viewBox attribute is a list of four numbers
# min-x, min-y, width and height, separated by whitespace and/or a comma
RE_VIEWBOX = re.compile(
    r"(<svg.+?)(\s*viewBox=[\"|\']([-\d,. ]+)[\"|\'])(.+?>)", re.DOTALL)

log = logging.getLogger('make_svg_font')


def parse_viewbox_values(vb_str):
    """
    Input: viewbox's values string
    Return: list of integers or floats of viewbox's values
    """
    list_str = re.split(r'[\s,]', vb_str)
    assert len(list_str) == 4, 'viewBox must have 4 values'
    return [literal_eval(val) for val in list_str]


def adjust_viewbox(svg_str, x_shift=0, y_shift=0, scale=1):
    """
    Changes viewbox's values.

    The regex match will contain 4 groups:
        1. String from '<svg' up to the space before 'viewBox'
        2. The whole 'viewBox' property (e.g. ' viewBox="0 100 128 128"')
        3. The 'viewBox' values
        4. Remainder of the '<svg>' element
    """
    vb = RE_VIEWBOX.search(svg_str)
    if vb:
        min_x, min_y, width, height = parse_viewbox_values(vb.group(3))
        new_svg_header = '{} viewBox="{} {} {} {}"{}'.format(
            vb.group(1), min_x + x_shift, min_y + y_shift,
            width * scale, height * scale, vb.group(4))
        svg_str = RE_VIEWBOX.sub(new_svg_header, svg_str)
    return svg_str


def clean_svg_doc(svg_str):
    # Remove XML header
    svg_str = RE_XMLHEADER.sub('', svg_str)

    # Remove all 'enable-background' parameters
    for enable_bkgd in RE_ENABLEBKGD.findall(svg_str):
        svg_str = svg_str.replace(enable_bkgd, '')

    # Remove white space between elements
    for space in RE_SPACEBTWEEN.findall(svg_str):
        svg_str = svg_str.replace(space, '><')

    return svg_str


def set_svg_id(data, gid):
    id_value = RE_SVGID.search(data)
    if id_value:
        return re.sub(id_value.group(1), 'id="glyph{}"'.format(gid), data)
    return re.sub('<svg', '<svg id="glyph{}"'.format(gid), data)


def add_svg_table(font_path, file_paths, compress_table=False):
    gnames_dict = {}  # key: glyph name; value: SVG file path
    for fpath in file_paths:
        fname = os.path.splitext(os.path.basename(fpath))[0]  # trim extension
        if fname.startswith(FILE_PREFIX):
            gname = fname[len(FILE_PREFIX):]
        else:
            gname = fname
        # validate glyph name
        if not glyph_name_is_valid(gname, fpath):
            continue
        # skip any duplicates and 'space'
        if gname in gnames_dict or gname == 'space':
            log.warning("Skipped file '{}'. The glyph name derived from it "
                        "is either a duplicate or 'space'".format(fpath))
            continue
        # limit the length of glyph name to 31 chars
        if len(gname) > 31:
            num = 0
            trimmed_gname = get_trimmed_glyph_name(gname, num)
            while trimmed_gname in gnames_dict:
                num += 1
                trimmed_gname = get_trimmed_glyph_name(trimmed_gname, num)
            gnames_dict[trimmed_gname] = fpath
            log.warning("Glyph name '{}' was trimmed to 31 characters: "
                        "'{}'".format(gname, trimmed_gname))
        else:
            gnames_dict[gname] = fpath

    font = TTFont(font_path)
    svg_docs_dict = {}
    for gname, svg_file_path in gnames_dict.items():
        try:
            gid = font.getGlyphID(gname)
        except KeyError:
            log.warning('Could not find a glyph named {} in the font'
                        ''.format(gname))
            continue

        with io.open(svg_file_path, encoding='utf-8') as fp:
            svg_item_data = fp.read()

        # Set id value
        svg_item_data = set_svg_id(svg_item_data, gid)

        # Scale and shift the artwork, by adjusting its viewBox
        svg_item_data = adjust_viewbox(
            svg_item_data, VIEWBOX_X_SHIFT, VIEWBOX_Y_SHIFT, VIEWBOX_SCALE)

        # Clean SVG document
        svg_item_data = clean_svg_doc(svg_item_data)

        svg_docs_dict[gid] = (svg_item_data.strip(), gid, gid)

    # Don't modify the input font if there's no SVG data
    if not svg_docs_dict:
        log.warning('None of the SVG files found could be added to the font')
        font.close()
        return

    # Make a list of the SVG documents sorted by GID
    svg_docs_list = sorted(svg_docs_dict.values(), key=lambda doc: doc[1])

    svg_table = newTable('SVG ')
    svg_table.compressed = compress_table
    svg_table.docList = svg_docs_list
    svg_table.colorPalettes = None
    font['SVG '] = svg_table

    ext = '.ttf' if 'glyf' in font else '.otf'
    svg_font_filename = '{}{}'.format(PS_NAME, ext)
    svg_font_path = os.path.join(os.path.dirname(font_path), svg_font_filename)
    font.save(svg_font_path)
    font.close()
    log.info("Wrote '{}' containing {} SVG glyphs".format(
             os.path.basename(svg_font_path), len(svg_docs_list)))
    return svg_font_path


def update_tables(font_path, revision):
    font = TTFont(font_path)
    font['head'].fontRevision = float(revision)
    if 'CFF ' in font:
        cff = font['CFF '].cff
        cff_font = cff[cff.fontNames[0]]
        top_dict = cff_font.rawDict
        top_dict['version'] = revision
        top_dict['FullName'] = FULL_NAME
        top_dict['FamilyName'] = FAMILY_NAME
        cff.fontNames = [PS_NAME]
    VERSION_STRING = 'Version {};{}'.format(revision, VENDOR)
    UNIQUE_ID = '{};{};{}'.format(revision, VENDOR, PS_NAME)
    name_strings = {
        1: FAMILY_NAME,
        3: UNIQUE_ID,
        4: FULL_NAME,
        5: VERSION_STRING,
        6: PS_NAME,
    }
    name_table = font['name']
    for nameID, string in name_strings.items():
        name_table.setName(string, nameID, 3, 1, 0x409)  # Windows only
    font.save(font_path)
    font.close()
    log.info('Updated font tables.')


def get_font_revision_number(font_path):
    with TTFont(font_path) as font:
        font_rev = font['head'].fontRevision
    return Decimal(font_rev).quantize(Decimal('1.000'))


def validate_font_path(path_str):
    valid_file_path = validate_file_path(path_str)
    try:
        TTFont(valid_file_path).close()
    except TTLibError as err:
        raise argparse.ArgumentTypeError(
            'Input file is n{}'.format(err.args[0][1:]))
    return valid_file_path


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
        '-z',
        action='store_true',
        dest='compress_table',
        help='compress the SVG table'
    )
    parser.add_argument(
        '-r',
        '--revision',
        help=("the font's revision number. Defaults to the revision number "
              "of the input font."),
        type=validate_revision_number,
    )
    parser.add_argument(
        'in_dir',
        help='input directory containing SVG files',
        metavar='DIR',
        type=validate_dir_path,
    )
    parser.add_argument(
        'in_font',
        help='input font',
        metavar='FONT',
        type=validate_font_path,
    )
    opts = parser.parse_args(args)

    if not opts.verbose:
        level = "WARNING"
    elif opts.verbose == 1:
        level = "INFO"
    else:
        level = "DEBUG"
    logging.basicConfig(level=level)

    file_paths = sorted(
        glob.iglob(os.path.join(opts.in_dir, '*.[sS][vV][gG]')))
    file_count = len(file_paths)

    if not file_count:
        log.error('Failed to match any SVG files.')
        return 1

    log.info("Found {} SVG files in '{}'".format(file_count, opts.in_dir))

    font_path = add_svg_table(opts.in_font, file_paths, opts.compress_table)
    if not font_path:
        return 1

    if not opts.revision:
        revision = get_font_revision_number(opts.in_font)
    else:
        revision = opts.revision

    update_tables(font_path, revision)


if __name__ == "__main__":
    sys.exit(main())
