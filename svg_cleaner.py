#!/usr/bin/env python
# Copyright 2015 Google, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Google Author(s): Doug Felt

"""Clean SVG.

svgo could do this, but we're fussy. Also, emacs doesn't understand
that 'style' defaults to 'text/css' and svgo strips this out by
default.

The files we're getting that are exported from AI contain lots of extra
data so that it can reimport the svg, and we don't need it."""

import argparse
import glob
import io
import logging
import os
import re
import shutil
import sys

from xml.parsers import expat
from xml.sax import saxutils

log = logging.getLogger('svg_cleaner')

# Expat doesn't allow me to identify empty tags (in particular, with an
# empty tag the parse location for the start and end is not the same) so I
# have to take a dom-like approach if I want to identify them. There are a
# lot of empty tags in svg. This way I can do some other kinds of cleanup
# as well (remove unnecessary 'g' elements, for instance).

# Use nodes instead of tuples and strings because it's easier to mutate
# a tree of these, and cleaner will want to do this.


class _Elem_Node(object):
    def __init__(self, name, attrs, contents):
        self.name = name
        self.attrs = attrs
        self.contents = contents

    def __repr__(self):
        line = ["elem(name: '%s'" % self.name]
        if self.attrs:
            line.append(" attrs: '%s'" % self.attrs)
        if self.contents:
            line.append(" contents[%s]: '%s'" % (len(self.contents),
                                                 self.contents))
        line.append(')')
        return ''.join(line)


class _Text_Node(object):
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return "text('%s')" % self.text


class SvgCleaner(object):
    """
    Strip out unwanted parts of an svg file, primarily the xml declaration
    and doctype lines, comments, and some attributes of the outermost <svg>
    element.

    The id will be replaced when it is inserted into the font.

    (viewBox causes unwanted scaling when used in a font and its effect is
    difficult to predict, but for outside a font we need to keep it sometimes
    so we keep it).

    version is unneeded

    xml:space is ignored (we're processing spaces so a request to maintain
    them has no effect).

    enable-background appears to have no effect.

    x and y on the outermost svg element have no effect.

    We keep width and height, and will elsewhere assume these are the
    dimensions used for the character box.
    """

    def __init__(self, strip=False, color=True):
        self.reader = SvgCleaner._Reader()
        self.cleaner = SvgCleaner._Cleaner(color)
        self.writer = SvgCleaner._Writer(strip)

    class _Reader(object):
        """
        Loosely based on fonttools's XMLReader. This generates a tree of nodes,
        either element nodes or text nodes. Successive text content is merged
        into one node, so contents will never contain more than one _Text_Node
        in a row. This drops comments, xml declarations, and doctypes.
        """

        def _reset(self, parser):
            self._stack = []
            self._textbuf = []

        def _start_element(self, name, attrs):
            self._flush_textbuf()
            node = _Elem_Node(name, attrs, [])
            if len(self._stack):
                self._stack[-1].contents.append(node)
            self._stack.append(node)

        def _end_element(self, name):
            self._flush_textbuf()
            if len(self._stack) > 1:
                self._stack = self._stack[:-1]

        def _character_data(self, data):
            if len(self._stack):
                self._textbuf.append(data)

        def _flush_textbuf(self):
            if self._textbuf:
                node = _Text_Node(''.join(self._textbuf))
                self._stack[-1].contents.append(node)
                self._textbuf = []

        def from_text(self, data):
            """Return the root node of a tree representing the svg data."""

            parser = expat.ParserCreate()
            parser.StartElementHandler = self._start_element
            parser.EndElementHandler = self._end_element
            parser.CharacterDataHandler = self._character_data
            self._reset(parser)
            parser.Parse(data)
            return self._stack[0]

    class _Cleaner(object):
        def __init__(self, color):
            log.warning('cleaner color: %s' % color)
            self._color = color

        def _clean_elem(self, node):
            viewBox, x, y, width, height = None, None, None, None, None
            nattrs = {}
            for k, v in node.attrs.items():
                if not self._color:
                    if k in ['class', 'style'] or k.startswith('xmlns:xlink'):
                        continue
                if node.name == 'svg' and k in [
                        'x', 'y', 'id', 'version', 'viewBox', 'width',
                        'height', 'enable-background', 'xml:space',
                        'xmlns:graph', 'xmlns:i', 'xmlns:x']:
                    if k == 'viewBox':
                        viewBox = v
                    elif k == 'width':
                        width = v
                    elif k == 'height':
                        height = v
                    elif k.startswith('xmlns:') and 'ns.adobe.com' not in v:
                        # keep if not an adobe namespace
                        log.debug('keep "%s" = "%s"' % (k, v))
                        nattrs[k] = v
                    log.debug('removing %s=%s' % (k, v))
                    continue
                v = re.sub(r'\s+', ' ', v)
                nattrs[k] = v

            if node.name == 'svg':
                if viewBox:
                    x, y, width, height = viewBox.split()
                if not width or not height:
                    if not viewBox:
                        raise ValueError('no viewBox, width, or height')
                nattrs['width'] = width
                nattrs['height'] = height
                # keep for svg use outside of font
                if viewBox and (int(x) != 0 or int(y) != 0):
                    log.warn('viewbox "%s" x: %s y: %s' % (viewBox, x, y))
                    nattrs['viewBox'] = viewBox
            node.attrs = nattrs

            # if display:none, skip this and its children
            style = node.attrs.get('style')
            if (style and 'display:none' in style) or (
                    node.attrs.get('display') == 'none'):
                node.contents = []
                return

            # Scan contents.
            # Remove any empty text nodes, or empty 'g' element nodes.
            # If a 'g' element has no attrs and only one subnode,
            # replace it with the subnode.
            wpos = 0
            for n in node.contents:
                if isinstance(n, _Text_Node):
                    if not n.text:
                        continue
                elif n.name == 'g':
                    if not n.contents:
                        continue
                    if 'i:extraneous' in n.attrs:
                        del n.attrs['i:extraneous']
                    if not n.attrs and len(n.contents) == 1:
                        n = n.contents[0]
                elif n.name == 'i:pgf' or n.name == 'foreignObject':
                    continue
                elif n.name == 'switch' and len(n.contents) == 1:
                    n = n.contents[0]
                elif n.name == 'style':
                    # some emacsen don't default 'style' properly,
                    # so leave this in.
                    if False and n.attrs.get('type') == 'text/css':
                        del n.attrs['type']

                if not self._color:
                    if not isinstance(n, _Text_Node) and n.name in [
                            'style', 'linearGradient', 'radialGradient']:
                        continue

                node.contents[wpos] = n
                wpos += 1
            if wpos < len(node.contents):
                node.contents = node.contents[:wpos]

        def _clean_text(self, node):
            text = node.text.strip()
            # common case is text is empty (line endings between elements)
            if text:
                # main goal here is to leave linefeeds in for style elements
                text = re.sub(r'[ \t]*\n+[ \t]*', '\n', text)
                text = re.sub(r'[ \t]+', ' ', text)
            node.text = text

        def clean(self, node):
            if isinstance(node, _Text_Node):
                self._clean_text(node)
            else:
                # do contents first, so we can check for empty subnodes after
                for n in node.contents:
                    self.clean(n)
                self._clean_elem(node)

    class _Writer(object):
        """
        For text nodes, replaces sequences of whitespace with a single space.
        For elements, replaces sequences of whitespace in attributes, and
        removes unwanted attributes from <svg> elements.
        """
        def __init__(self, strip):
            log.warning('writer strip: %s' % strip)
            self._strip = strip

        def _write_node(self, node, lines, indent):
            """
            Node is a node generated by _Reader, either a TextNode or an
            ElementNode. Lines is a list to collect the lines of output.
            Indent is the indentation level for this node.
            """
            if isinstance(node, _Text_Node):
                if node.text:
                    lines.append(node.text)
            else:
                margin = '' if self._strip else '  ' * indent
                line = [margin]
                line.append('<%s' % node.name)
                # custom sort attributes of svg, yes this is a hack
                if node.name == 'svg':
                    def svgsort(k):
                        if k == 'width':
                            return (0, None)
                        elif k == 'height':
                            return (1, None)
                        else:
                            return (2, k)
                    ks = sorted(node.attrs.keys(), key=svgsort)
                else:
                    def defsort(k):
                        if k == 'id':
                            return (0, None)
                        elif k == 'class':
                            return (1, None)
                        else:
                            return (2, k)
                    ks = sorted(node.attrs.keys(), key=defsort)
                for k in ks:
                    v = node.attrs[k]
                    line.append(' %s=%s' % (k, saxutils.quoteattr(v)))
                if node.contents:
                    line.append('>')
                    lines.append(''.join(line))
                    for elem in node.contents:
                        self._write_node(elem, lines, indent + 1)
                    line = [margin]
                    line.append('</%s>' % node.name)
                    lines.append(''.join(line))
                else:
                    line.append('/>')
                    lines.append(''.join(line))

        def to_text(self, root):
            # set up lines for recursive calls, let them append lines,
            # then return the result.
            lines = []
            self._write_node(root, lines, 0)
            return ''.join(lines) if self._strip else '\n'.join(lines)

    def tree_from_text(self, svg_text):
        return self.reader.from_text(svg_text)

    def clean_tree(self, svg_tree):
        self.cleaner.clean(svg_tree)

    def tree_to_text(self, svg_tree):
        return self.writer.to_text(svg_tree)

    def clean_svg(self, svg_text):
        """Return the cleaned svg_text."""
        tree = self.tree_from_text(svg_text)
        self.clean_tree(tree)
        return self.tree_to_text(tree)


def clean_svg_files(file_paths, out_dir, strip=False, color=True):
    count = 0

    cleaner = SvgCleaner(strip, color)

    for svg_file_path in file_paths:
        log.debug('read: %s', svg_file_path)
        with io.open(svg_file_path, encoding='utf-8') as in_fp:
            result = cleaner.clean_svg(in_fp.read())

        if out_dir:
            out_path = os.path.join(out_dir, os.path.basename(svg_file_path))
        else:
            out_path = svg_file_path

        with io.open(out_path, 'w', encoding='utf-8') as out_fp:
            log.debug('write: %s', out_path)
            out_fp.write(result)
            count += 1

    if out_dir:
        out_folder = out_dir
    else:
        out_folder = os.path.dirname(out_path)

    log.info("Saved {} clean SVG files in '{}'.".format(count, out_folder))


def _validate_dir_path(path_str):
    valid_path = os.path.abspath(os.path.realpath(path_str))
    if not os.path.isdir(valid_path):
        raise argparse.ArgumentTypeError(
            "{} is not a valid directory path.".format(path_str))
    return _normalize_path(path_str)


def _normalize_path(path_str):
    return os.path.normpath(path_str)


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Remove superfluous data from SVG files.")
    parser.add_argument(
        '-v',
        '--verbose',
        help='verbose mode\n'
             'Use -vv for debug mode',
        action='count',
        default=0
    )
    parser.add_argument(
        'in_dir',
        help='input directory',
        metavar='DIR',
        type=_validate_dir_path,
    )
    parser.add_argument(
        '-o',
        '--out-dir',
        help='output directory. Defaults to input directory.',
        metavar='DIR',
        type=_normalize_path,
    )
    parser.add_argument(
        '-w',
        '--strip-whitespace',
        help='remove newlines and indentation',
        action='store_true'
    )
    parser.add_argument(
        '-k',
        '--kind',
        help='select the kind of SVGs being processed (default: %(default)s)',
        choices=('bw', 'color'),
        default='color'
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
        log.warning('Failed to match any SVG files.')
        return 1

    log.info("Found {} SVG files in '{}'.".format(file_count, opts.in_dir))

    if opts.out_dir:
        out_path = os.path.abspath(os.path.realpath(opts.out_dir))
        # if directory exists, delete it
        if os.path.isdir(out_path):
            shutil.rmtree(out_path)
            log.info("Deleted directory '{}'.".format(opts.out_dir))
        # if it's NOT a directory, but exists nevertheless
        elif os.path.exists(out_path):
            os.remove(out_path)
            log.info("Deleted file '{}'.".format(opts.out_dir))
        # make directory
        os.makedirs(out_path)

    clean_svg_files(file_paths, opts.out_dir,
                    strip=opts.strip_whitespace, color=(opts.kind == 'color'))


if __name__ == '__main__':
    sys.exit(main())
