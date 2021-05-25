# Noto Emoji SVG

OpenType-SVG version of [Noto Emoji](https://github.com/googlefonts/noto-emoji).

### :warning: NOTE :warning:

The repository contains aliases/symlinks. Cloning on Windows
requires using the option `-c core.symlinks=true` and running the command with
Admin privileges.

	git -c core.symlinks=true clone https://github.com/adobe-fonts/noto-emoji-svg.git

You may also need to pull using this command,

	git -c core.symlinks=true pull

and configure the repository with this command,

	git config core.symlinks true


### :warning: NOTE 2 :warning:

As of May 25 2021, the only browser that displays the OT-SVG font
correctly is **Microsoft Edge Legacy** (Tested in v44). Edge Legacy is the Chromium-free version of Edge. [Information on how to install Edge Legacy](https://techcommunity.microsoft.com/t5/discussions/tutorial-how-to-run-legacy-and-chromium-based-edge/m-p/1121216)

**Firefox** supports OT-SVG but has a problem in the way it displays
the SVG artwork: the size of the color artwork is correct only if the
font's UPM value is 1000. (Tested in v88.0)

**Safari** also supports OT-SVG, but the color artwork won't be
displayed if the font's `SVG` table contains more than 2000 items.
Also, whenever the matrix of a `gradientTransform` contains a zero
value the gradient fill won't be displayed. (Tested in v14.0)

**Google Chrome** does not support OT-SVG. (Tested in v90.0)


### Requirements

* Python 3.6+
* FontTools
* AFDKO


## Building the fonts

To build the **black-and-white font** use the following command,

	python3 make_bw_font.py -o fonts -r x.xxx --gsub GSUB.fea --gpos GPOS.fea --uvs UVS.txt svg_bw flags_bw

and to build the **color font** use the following command,

	python3 make_svg_font.py -z -r x.xxx svg flags fonts/NotoEmoji.otf -v

where `x.xxx` is the version number to be assigned to the font (e.g `1.082`).

It's possible to build both fonts (and to subroutinize the BW font) using the shell
script that combines all commands,

	sh build.sh x.xxx


## Subroutinizing the OTFs

The OT-CFF fonts can be subroutinized with the following command:

	sh subroutinize.sh <font file path>

Subroutinizing requires AFDKO's `tx` and `sfntedit` tools.


## Generating the HTML test document

To help thoroughly test the fonts, a script was developed that generates
[an HTML file](test.html) that lists all official emoji and emoji sequences.
The current output shows Unicode version 12.1. To generate the file run this command:

	python3 test/generate_test_html.py

To divide the output into multiple files use the `--paginate` option:

	python3 test/generate_test_html.py -p

To generate a subset of the **test.html** file —named **test-changes.html**— containing
only the changes from the previous font build, use the `-c/--changes` option. Keep in
mind that this option depends on the contents of the [changes.txt](test/changes.txt) file.


## Generating the TXT test document

Another script was developed that generates the test document in simple TXT format.
To generate the [TXT test file](test.txt) run this command:

	python3 test/generate_test_txt.py -e 20

This file can be easily imported into Illustrator, Photoshop or InDesign.

The [emoji-test.txt](test/emoji-test.txt) file was obtained from http://unicode.org/Public/emoji/

As with the HTML test document, it's possible to generate a subset file named
**test-changes.txt** by using the `-c/--changes` option.


## Generating aliases

Aliases/symbolic links are used extensively to avoid having multiple copies of the
same artwork.

To generate **SVG black-and-white aliases** run this command:

	python3 make_aliases.py emoji_bw_aliases.txt svg_bw

To generate **SVG color aliases** run this command:

	python3 make_aliases.py emoji_color_aliases.txt svg

To generate **PNG color aliases** run this command:

	python3 make_aliases.py emoji_color_aliases.txt png

To generate **SVG black-and-white flag aliases** run this command:

	python3 make_aliases.py flag_bw_aliases.txt flags_bw

To generate **SVG color flag aliases** run this command:

	python3 make_aliases.py flag_color_aliases.txt flags

To generate **PNG color flag aliases** run this command:

	python3 make_aliases.py flag_color_aliases.txt flags_png

## Generating PNG and SVG files

In the event that only the original Ai artwork files are provided, use the
following steps to generate PNG or SVG files:

1. Open the Adobe Illustrator file(s)
2. Select the menu File > Scripts > Other Script...
3. Pick one of the scripts from the folder [ai_scripts](ai_scripts)
4. Select a folder to save the output files into


## Cleaning/sanitizing the SVG artwork

Whenever the SVG files are edited and saved with Adobe Illustrator they contain
unnecessary data that can and should be removed.

To clean the **black-and-white artwork** run this command:

	python3 svg_cleaner.py -k bw svg_bw

To clean the **color artwork** run this command:

	python3 svg_cleaner.py svg


## Adobe Illustrator saving options

![SVG save options](Ai_save_options.png)
