#!/usr/bin/env sh

set -e

BW_FONT=NotoEmoji.otf

# get absolute path to bash script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

# build BW font
python3 $DIR/make_bw_font.py -o $DIR/fonts -r $1 --gsub $DIR/GSUB.fea --gpos $DIR/GPOS.fea --uvs $DIR/UVS.txt $DIR/svg_bw

# subroutinize BW font
sh $DIR/subroutinize.sh $DIR/fonts/$BW_FONT

# build color font
python3 $DIR/make_svg_font.py $DIR/svg $DIR/fonts/$BW_FONT -v -z
