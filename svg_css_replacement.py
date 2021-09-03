# Copyright © 2021 Adobe, Inc.
# Author: Frank Grießhammer
'''
Convert inline CSS in SVG files to SVG attributes
'''


import pathlib
import re


def convert_css_to_svg(attr_string):
    '''
    expects a string of inline CSS, and converts them to SVG attributes
    '''
    attributes = attr_string.split(';')
    svg_attrs = []
    for attribute in attributes:
        if attribute:
            # some lines end with ; and others don’t – this means there may be
            # an empty string
            attr_name, attr_value = attribute.split(':')
            svg_attrs.append(f'{attr_name}="{attr_value}"')
    return(' '.join(svg_attrs))


# find all SVGs in all folders that may contain them
svgs = []
folders = ['svg', 'svg_bw', 'flags', 'flags_bw']
for folder in folders:
    svgs.extend(pathlib.Path(folder).glob('*.svg'))

for svg in svgs:
    with open(svg, 'r') as svg_in:
        svg_data = svg_in.read()

    # check if a SVG even contains an inline style
    if re.findall(r'style="', svg_data):
        print('fixing', svg)
        fixed_svg = []
        for line in svg_data.splitlines():
            # if it does, fix the styles on a line-by-line basis
            style_match = re.match(r'.+(style="(.+?)").*', line)
            if style_match:
                css_inline_style = style_match.group(1)
                css_attrs = style_match.group(2)
                svg_attrs = convert_css_to_svg(css_attrs)
                fixed_line = line.replace(
                    style_match.group(1), svg_attrs)
                fixed_svg.append(fixed_line)
            else:
                fixed_svg.append(line)

        # save the SVG
        with open(svg, 'w') as svg_out:
            svg_out.write('\n'.join(fixed_svg))
