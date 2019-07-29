#!/usr/bin/env sh

# Subroutinizes an OT-CFF font using AFDKO's tx and sfntedit tools

set -e

tx -cff +S +b -std "$1" tb_cff
sfntedit -a CFF=tb_cff "$1"
rm tb_cff
