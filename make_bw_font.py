# Copyright © 2019 Adobe, Inc.
# Author: Miguel Sousa
"""
Creates a sans-color emoji OT-CFF font from b&w SVG files.
"""
import argparse
from collections import deque
import glob
import io
import logging
import os
import re
import sys

from fontTools.feaLib.builder import addOpenTypeFeatures
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.psCharStrings import T2CharString
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.svgLib.path import SVGPath

COPYRIGHT = 'Copyright 2013 Google Inc.'
TRADEMARK = 'Noto is a trademark of Google Inc.'
FAMILY_NAME = 'Noto Emoji'
STYLE_NAME = 'Regular'
FULL_NAME = FAMILY_NAME
PS_NAME = 'NotoEmoji'
MANUFACTURER = 'Google Inc. & Adobe Inc.'
DESIGNER = 'Google Inc.'
VENDOR = 'GOOG'
VENDOR_URL = 'http://www.google.com/get/noto/'
DESIGNER_URL = VENDOR_URL
LICENSE = ('This Font Software is licensed under the SIL Open Font License, '
           'Version 1.1. This Font Software is distributed on an "AS IS" '
           'BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either '
           'express or implied. See the SIL Open Font License for the '
           'specific language, permissions and limitations governing your '
           'use of this Font Software.')
LICENSE_URL = 'http://scripts.sil.org/OFL'
FSTYPE = 0  # Installable embedding

SVG_SIZE = 128
UPM = 2048
EMOJI_H_ADV = 2550
EMOJI_V_ADV = 2500
EMOJI_SIZE = 2400  # ASCENT + abs(DESCENT)
ABOVE_BASELINE = 0.7451  # ASCENT / EMOJI_H_ADV
ASCENT = 1900
DESCENT = -500
UNDERLINE_POSITION = -1244
UNDERLINE_THICKNESS = 131


SPACE_CHARSTRING = T2CharString(program=[EMOJI_H_ADV, 'endchar'])

RE_UNICODE = re.compile(r'^u[0-9a-f]{4,5}$', re.IGNORECASE)
RE_REVISION = re.compile(r'^[0-9]{1,3}\.[0-9]{3}$')

VALID_1STCHARS = tuple('_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
VALID_CHARS = VALID_1STCHARS + tuple('.0123456789')

log = logging.getLogger('make_bw_font')


def draw_notdef(pen):
    em_10th = EMOJI_H_ADV / 10
    v_shift = EMOJI_H_ADV * (ABOVE_BASELINE - 1)
    pen.moveTo((em_10th * 2, em_10th * 1 + v_shift))
    pen.lineTo((em_10th * 8, em_10th * 1 + v_shift))
    pen.lineTo((em_10th * 8, em_10th * 9 + v_shift))
    pen.lineTo((em_10th * 2, em_10th * 9 + v_shift))
    pen.closePath()
    pen.moveTo((em_10th * 3, em_10th * 2 + v_shift))
    pen.lineTo((em_10th * 3, em_10th * 8 + v_shift))
    pen.lineTo((em_10th * 7, em_10th * 8 + v_shift))
    pen.lineTo((em_10th * 7, em_10th * 2 + v_shift))
    pen.closePath()


def glyph_name_is_valid(gname, fpath):
    """
    Validates a string meant to be used as a glyph name, following the rules
    defined at https://adobe-type-tools.github.io/afdko/...
                       OpenTypeFeatureFileSpecification.html#2.f.i
    Returns True if the glyph name is valid and False otherwise.
    """
    if not gname:
        log.warning("Unable to get a glyph name from file '{}'.".format(fpath))
        return False
    elif gname[0] not in VALID_1STCHARS:
        log.warning("Glyph name made from file '{}' starts with an invalid "
                    "character '{}'.".format(fpath, gname[0]))
        return False
    elif not all([char in VALID_CHARS for char in tuple(gname)]):
        log.warning("Glyph name made from file '{}' contains one or more "
                    "invalid characters.".format(fpath))
        return False
    return True


def get_trimmed_glyph_name(gname, num):
    """
    Glyph names cannot have more than 31 characters.
    See https://docs.microsoft.com/en-us/typography/opentype/spec/...
               recom#39post39-table
    Trims an input string and appends a number to it.
    """
    suffix = '_{}'.format(num)
    return gname[:31 - len(suffix)] + suffix


def make_font(file_paths, out_dir, revision, gsub_path, gpos_path, uvs_lst):
    cmap, gorder, validated_fpaths = {}, deque(), []
    # build glyph order
    for fpath in file_paths:
        # derive glyph name from file name
        gname = os.path.splitext(os.path.basename(fpath))[0]  # trim extension
        # validate glyph name
        if not glyph_name_is_valid(gname, fpath):
            continue
        # skip any duplicates and 'space'
        if gname in gorder or gname == 'space':
            log.warning("Skipped file '{}'. The glyph name derived from it "
                        "is either a duplicate or 'space'.".format(fpath))
            continue
        # limit the length of glyph name to 31 chars
        if len(gname) > 31:
            num = 0
            trimmed_gname = get_trimmed_glyph_name(gname, num)
            while trimmed_gname in gorder:
                num += 1
                trimmed_gname = get_trimmed_glyph_name(trimmed_gname, num)
            gorder.append(trimmed_gname)
            log.warning("Glyph name '{}' was trimmed to 31 characters: "
                        "'{}'".format(gname, trimmed_gname))
        else:
            gorder.append(gname)
        validated_fpaths.append(fpath)

        # add to cmap
        if RE_UNICODE.match(gname):
            uni_int = int(gname[1:], 16)  # trim leading 'u'
            cmap[uni_int] = gname

    fb = FontBuilder(UPM, isTTF=False)
    fb.font['head'].fontRevision = float(revision)
    fb.font['head'].lowestRecPPEM = 12

    cs_dict = {}
    cs_cache = {}
    for i, svg_file_path in enumerate(validated_fpaths):
        svg_file_realpath = os.path.realpath(svg_file_path)

        if svg_file_realpath not in cs_cache:
            pen = T2CharStringPen(EMOJI_H_ADV, None)
            svg = SVGPath(svg_file_realpath,
                          transform=(EMOJI_SIZE / SVG_SIZE, 0, 0,
                                     -EMOJI_SIZE / SVG_SIZE,
                                     (EMOJI_H_ADV * .5) - (EMOJI_SIZE * .5),
                                     EMOJI_H_ADV * ABOVE_BASELINE))
            svg.draw(pen)
            cs = pen.getCharString()
            cs_cache[svg_file_realpath] = cs
        else:
            cs = cs_cache.get(svg_file_realpath)

        cs_dict[gorder[i]] = cs

    # add '.notdef', 'space' and zero-width joiner
    gorder.extendleft(reversed(['.notdef', 'space', 'ZWJ']))
    pen = T2CharStringPen(EMOJI_H_ADV, None)
    draw_notdef(pen)
    cs_dict.update({'.notdef': pen.getCharString(),
                    'space': SPACE_CHARSTRING,
                    'ZWJ': SPACE_CHARSTRING,
                    })
    cmap.update({32: 'space',   # U+0020
                 160: 'space',  # U+00A0
                 8205: 'ZWJ',   # U+200D
                 })

    fb.setupGlyphOrder(list(gorder))  # parts of FontTools require a list
    fb.setupCharacterMap(cmap, uvs=uvs_lst)
    fb.setupCFF(PS_NAME, {'version': revision,
                          'Notice': TRADEMARK,
                          'Copyright': COPYRIGHT,
                          'FullName': FULL_NAME,
                          'FamilyName': FAMILY_NAME,
                          'Weight': STYLE_NAME}, cs_dict, {})

    glyphs_bearings = {}
    for gname, cs in cs_dict.items():
        gbbox = cs.calcBounds(None)
        if gbbox:
            xmin, ymin, _, ymax = gbbox
            if ymax > ASCENT:
                log.warning("Top of glyph '{}' may get clipped. "
                            "Glyph's ymax={}; Font's ascent={}".format(
                                gname, ymax, ASCENT))
            if ymin < DESCENT:
                log.warning("Bottom of glyph '{}' may get clipped. "
                            "Glyph's ymin={}; Font's descent={}".format(
                                gname, ymin, DESCENT))
            lsb = xmin
            tsb = EMOJI_V_ADV - ymax - EMOJI_H_ADV * (1 - ABOVE_BASELINE)
            glyphs_bearings[gname] = (lsb, tsb)
        else:
            glyphs_bearings[gname] = (0, 0)

    h_metrics = {}
    v_metrics = {}
    for gname in gorder:
        h_metrics[gname] = (EMOJI_H_ADV, glyphs_bearings[gname][0])
        v_metrics[gname] = (EMOJI_V_ADV, glyphs_bearings[gname][1])
    fb.setupHorizontalMetrics(h_metrics)
    fb.setupVerticalMetrics(v_metrics)

    fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT)

    v_ascent = EMOJI_H_ADV // 2
    v_descent = EMOJI_H_ADV - v_ascent
    fb.setupVerticalHeader(
        ascent=v_ascent, descent=-v_descent, caretSlopeRun=1)

    VERSION_STRING = 'Version {};{}'.format(revision, VENDOR)
    UNIQUE_ID = '{};{};{}'.format(revision, VENDOR, PS_NAME)
    name_strings = dict(
        copyright=COPYRIGHT,             # ID 0
        familyName=FAMILY_NAME,          # ID 1
        styleName=STYLE_NAME,            # ID 2
        uniqueFontIdentifier=UNIQUE_ID,  # ID 3
        fullName=FULL_NAME,              # ID 4
        version=VERSION_STRING,          # ID 5
        psName=PS_NAME,                  # ID 6
        trademark=TRADEMARK,             # ID 7
        manufacturer=MANUFACTURER,       # ID 8
        designer=DESIGNER,               # ID 9
        vendorURL=VENDOR_URL,            # ID 11
        designerURL=DESIGNER_URL,        # ID 12
        licenseDescription=LICENSE,      # ID 13
        licenseInfoURL=LICENSE_URL,      # ID 14
    )
    fb.setupNameTable(name_strings, mac=False)

    fb.setupOS2(fsType=FSTYPE, achVendID=VENDOR, fsSelection=0x0040,  # REGULAR
                usWinAscent=ASCENT, usWinDescent=-DESCENT,
                sTypoAscender=ASCENT, sTypoDescender=DESCENT,
                sCapHeight=ASCENT, ulCodePageRange1=(1 << 1))  # set 1st CP bit

    if gsub_path:
        addOpenTypeFeatures(fb.font, gsub_path, tables=['GSUB'])

    if gpos_path:
        addOpenTypeFeatures(fb.font, gpos_path, tables=['GPOS'])

    fb.setupPost(isFixedPitch=1,
                 underlinePosition=UNDERLINE_POSITION,
                 underlineThickness=UNDERLINE_THICKNESS)

    fb.setupDummyDSIG()

    fb.save(os.path.join(out_dir, '{}.otf'.format(PS_NAME)))


def parse_uvs_file(file_path):
    """
    Parses an Unicode Variation Sequences text file.
    Returns a list of tuples in the form
    (unicodeValue, variationSelector, glyphName).
    'unicodeValue' and 'variationSelector' are integer code points.
    'glyphName' may be None, to indicate this is the default variation.
    """
    with io.open(file_path, encoding='utf-8') as fp:
        lines = fp.read().splitlines()

    uvs_list = []
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        uni_str, gname = line.split(';')
        uni_lst = uni_str.strip().split()
        if not isinstance(uni_lst, list) and len(uni_lst) != 2:
            log.error('Line #{} is not correctly formatted.'.format(i))
            continue
        try:
            uni_int = [int(cdpt, 16) for cdpt in uni_lst]
        except ValueError:
            log.error('Line #{} has an invalid code point.'.format(i))
            continue
        gname = gname.strip()
        if gname == 'None':
            gname = None
        uni_int.append(gname)
        uvs_item = tuple(uni_int)
        if uvs_item in uvs_list:
            log.warning('Line #{} is a duplicate UVS.'.format(i))
            continue
        uvs_list.append(uvs_item)
    if not uvs_list:
        log.warning('No Unicode Variation Sequences were found.')
        return None
    return uvs_list


def validate_dir_path(path_str):
    valid_path = os.path.abspath(os.path.realpath(path_str))
    if not os.path.isdir(valid_path):
        raise argparse.ArgumentTypeError(
            "{} is not a valid directory path.".format(path_str))
    return normalize_path(path_str)


def validate_file_path(path_str):
    valid_path = os.path.abspath(os.path.realpath(path_str))
    if not os.path.isfile(valid_path):
        raise argparse.ArgumentTypeError(
            "{} is not a valid file path.".format(path_str))
    return normalize_path(path_str)


def normalize_path(path_str):
    return os.path.normpath(path_str)


def validate_revision_number(rev_str):
    if not RE_REVISION.match(rev_str):
        raise argparse.ArgumentTypeError(
            "The revision number must follow this format: 123.456")
    return rev_str


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
        'in_dir',
        help='input directory containing SVG files',
        metavar='DIR',
        type=validate_dir_path,
    )
    parser.add_argument(
        '-o',
        '--out-dir',
        help='directory to save the font in. Defaults to input directory.',
        metavar='DIR',
        type=normalize_path,
    )
    parser.add_argument(
        '-r',
        '--revision',
        help="the font's revision number. Defaults to %(default)s",
        type=validate_revision_number,
        default='0.001',
    )
    parser.add_argument(
        '--gsub',
        help='path to GSUB features file',
        type=validate_file_path,
    )
    parser.add_argument(
        '--gpos',
        help='path to GPOS features file',
        type=validate_file_path,
    )
    parser.add_argument(
        '--uvs',
        help='path to Unicode Variation Sequences file',
        type=validate_file_path,
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

    log.info("Found {} SVG files in '{}'.".format(file_count, opts.in_dir))

    uvs = None
    if opts.uvs:
        uvs = parse_uvs_file(opts.uvs)

    if opts.out_dir:
        out_path = os.path.abspath(os.path.realpath(opts.out_dir))
        # create directory if it doesn't exist
        if not os.path.exists(out_path):
            os.makedirs(out_path)
        # the path exists but it's NOT a directory
        elif not os.path.isdir(out_path):
            log.error("'{}' is not a directory.".format(opts.out_dir))
            return 1
        out_dir = opts.out_dir
    else:
        out_dir = opts.in_dir

    make_font(file_paths, out_dir, opts.revision, opts.gsub, opts.gpos, uvs)


if __name__ == "__main__":
    sys.exit(main())
