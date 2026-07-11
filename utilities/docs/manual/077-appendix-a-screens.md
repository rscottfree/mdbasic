---
name: APPENDIX A: SCREENS
order: 77
token: none
---

LOADING/SAVING SCREENS AND FONTS

SAVE"filename", device, secondary

This is the CBM BASIC standard syntax
for saving/loading programs. Valid
secondary address numbers are 0-31 for
serial devices; 32-127 for other
devices.

MDBASIC utilizes the secondary address
numbers 16, 17 and 18. These numbers
define which type of information to save
or load. The secondary addresses and the
information they represent are as
follows:

16 = Video Matrix - screen text and
colors (2K)
17 = Character Set - custom character
set (4K)
18 = Bitmap Graphics - plotted dots and
colors (10K)

A file saved with these secondary
addresses can only be loaded by the same
secondary address. The following are
some examples of loading & saving.

SAVE"SCREEN",8,16 :'save current text
screen with colors
LOAD"FONT",8,17 :'load redefined text
characters, use SCREEN 1 to show
LOAD"BITMAP",8,18 :'load and show a
bitmap screen (hires or multicolor)

NOTE: If a text screen in redefined
character mode is saved, only the scan
codes (poke codes) on the screen are
saved. The character shapes must be
saved in a separate file using secondary
address 17 with a different filename.

When loading/saving a text screen
(secondary=16) the data is loaded
loaded/saved from the RAM of the current
screen page. Below is the page memory
map:

| PAGE | SCREEN RAM |
|--|--|
| 0 | $0400-$07E7 |
| 1 | $C000-$C3E7 |
| 2 | $C400-$C7E7 |
| 3 | $C800-$CBE7 |
| 4 | $CC00-$CFE7 |

BINARY SAVE
You can specify the memory locations for
a save operation as follows:

SAVE start, end, filename$, device,
secondary

NOTE: The the filename$, device and
secondary parameters are optional. The
default device is 1 (tape) as usual.

SAVE $C000, $CFFF :'SAVE HIRAM TO TAPE –
NO FILENAME SAVE 49152, 53247,"HIRAM",8
:'SAVE HIRAM TO DISK – FILENAME REQUIRED
