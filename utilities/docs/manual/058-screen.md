---
name: SCREEN
order: 58
token: auto
---


PURPOSE:

To control the screen display including
page selection, color mode and fine
scrolling.

SYNTAX:
```text

SCREEN ON | OFF
SCREEN CLR
SCREEN [CLR] [page] [,colorMode]
[,offsetX] [,offsetY]
```

DESCRIPTION:

The screen statement controls the
display of the entire screen. There are
5 available pages which share the same
color RAM and cursor. The screen can be
turned ON or OFF which can improve CPU
performance. The screen borders can be
enlarged to hide the screen offset and
incoming characters being added to the
screen when fine-scrolling text or to
hide an enlarged sprite so that it does
not stick out of the border at its zero
axis. The screen offsets can also be
used to produce a full-screen shaking
effect.

SCREEN ON and SCREEN OFF
enables/disables the screen output. When
off, the color of the screen foreground
will match the color of the border. With
the screen off, CPU performance improves
since less traffic is on the data bus.
This can be used to accurately read
files on an old 1540 disk drive.

SCREEN CLR will clear the current
screen. If the screen is a bitmap then
the plotted dots are removed and the
background color is set according to the
values set by the last MAPCOL statement
(for standard/hires mode) or the COLOR
statement (for multicolor mode).

page (0-5) selects the page to display.
Pages 0-4 are 1K pages in text mode. On
first use, pages 1,2,3 & 4 require
initializing the character dot data
(DESIGN NEW or LOAD from file) which is
shared by these four pages. Page 5 is
the 8K bitmap page. Each page will need
to be cleared on first use. This can be
done flicker-free by preceding the page
parameter with the CLR keyword.

| PAGE | SCREEN RAM | SPRITE POINTERS | AVAILABLE RAM FOR SPRITES | SPRITE DATA INDEXES |
|--|--|--|--|--|
| 0 | $0400-$07E7 | $07F7-$07FF | $0340-$03FF, $0800-$3FBF | 13-15, 32-255 |
| 1 | $C000-$C3E7 | $C3F7-$C3FF | $C400-$CFFF | 16-63 |
| 2 | $C400-$C7E7 | $C7F7-$C7FF | $C000-$C3FF, $C800-$CFFF | 0-15, 32-63 |
| 3 | $C800-$CBE7 | $CBF7-$CBFF | $C000-$C7FF, $CC00-$CFFF | 0-31, 48-63 |
| 4 | $CC00-$CFE7 | $CFF7-$CFFF | $C000-$CBBF | 0-47 |
| 5 | $C800-$CBE7 | $CBF7-$CBFF | $C000-$C7FF, $CC00-$CFFF | 0-31, 48-63 |

NOTE: Page 3 is used by the bitmap
screen. Page 4 is used by the RS-232
I/O.

colorMode (0-2, default 0) is used to
select the color scheme for all screens.

| MODE | DESCRIPTION | TEXT | BITMAP |
|--|--|--|--|
| 0 | Standard (default) | 8x8 | 320x200 |
| 1 | Multicolor | 4x8 | 160x200 |
| 2 | Extended Background Color | 8x8 | n/a* |

*Extended background color mode is not
applicable to bitmap displays (page 5)
and thus will result in an ILLEGAL
QUANTITY ERROR.

Standard color mode is the default color
mode for both text and bitmap screens.
For text mode, each character can only
have one color (0-15) for all dots that
define the font in the 8 x 8 matrix. All
characters on the screen share the same
background color (0-15).

A standard color (hires) bitmap screen
can have each pixel with one of two
states, on or off. The pixels that
occupy the same 8 x 8 square will share
the same color (0-15) based on the pixel
state. Screen 3 is used by the bitmap
screen for this purpose. The color of
each 8 x 8 square corresponds to a
character on the video matrix. The
high-nybble determines the color for
pixels that are off. The low-nybble
determines the color for pixels that are
on.

Multicolor mode is used by both text and
bitmap screens. This mode increases the
number of colors available for each
character by reducing the number of
pixels used to display it. Each pixel is
represented by 2 bits. The bit pattern
determines the color source.

The COLOR statement is used to set all
colors for text screens. The background
color, cc1 and cc2 are common for all
characters on the screen. Any change is
visible immediately. The table below
lists the four 2-bit patterns and the
associated color source:

<!-- table: mode=sections -->
| PATTERN | COLOR | SOURCE | AVAILABLE COLORS |
|--|--|--|--|
| 00 | background color | background color reg 0 | 0-15 |
| 01 | cc1 | background color reg 1 | 0-15 |
| 10 | cc2 | background color reg 2 | 0-15 |
| 11 | foreground color | color RAM ($D800-$BDFF) | 0-7 select std color mode, first 3 bits, colors 0-7. 8-15 select multicolor of 0-7 |

If a character is printed to the screen
using colors 0-7, the character is
displayed in multicolor mode (4 x 8). If
it is printed using colors 8-15, the
character is displayed in standard mode
(8 x 8). This allows multicolor & hi-
resolution characters to be displayed on
the same screen at the same time, at
expense of loosing colors 0-7 for hires
mode.

If a character is not available in the
scan codes 0-63 then the DESIGN
statement can be used to define a custom
shape. Entire character sets can also be
loaded from a file into memory at
$F000-$FFFF. Multicolor character fonts
are typically made up of two characters
placed side-by-side with the shift key
characters used for the second half of
each character.

Extended background color mode enables
multiple background colors for each text
character. This mode increases the
number of background colors displayed by
reducing the number of characters that
can be shown on the screen. The only
displayable characters are the
characters with codes from 0-63 (5-bit
value). The upper 2 bits are used to
select the source of the color. Codes
64-255 select a different background
color but still display the same
character of codes 0-63. The COLOR
statement is used to set the colors to
be selectable by each bit pair.

<!-- table: mode=sections -->
| PATTERN | COLOR | CODES | SOURCE | AVAILABLE COLORS |
|--|--|--|--|--|
| 00 | background color | 0-63 | background color reg 0 | 0-15 |
| 01 | cc1 | 64-127 | background color reg 1 | 0-15 |
| 10 | cc2 | 128-191 | background color reg 2 | 0-15 |
| 11 | cc3 | 192-255 | background color reg 3 | 0-15 |

Extended background color mode can be
used to produce a window-like effect on
sections of text because a different
background color makes text stand out
from surrounding text having another
background color. The COLOR statement
can be used to change the background
colors of these windows instantly to
highlight a particular section of text
on the screen or produce a flashing
effect. Extended background color mode
is not applicable to bitmap displays
(page 5) and will result in an ILLEGAL
QUANTITY ERROR.

offsetX (0-15, default 8) controls the
horizontal foreground offset and border
size. Values 0-7 set the offset with 38
visible columns. Values 8-15 set the
same offset but with 40 visible columns.

offsetY (0-15, default 11) controls the
vertical foreground offset and border
size. Values 0-7 set the offset with 24
visible rows. Values 8-15 set the same
offset but with 25 visible rows.

EXAMPLE:
```text

SCREEN OFF:WAIT60:SCREEN ON :'TURN
SCREEN OUTPUT OFF FOR 60 JIFFIES
SCREEN,,0 :'38 COLUMNS (EXPANDED SIDE
BORDERS)
SCREEN 0,0,8,11 :'STANDARD C64 TEXT
SCREEN
SCREEN CLR 5,0 :'INIT AND SHOW HIRES
BITMAP
DESIGN NEW:SCREEN CLR 1 :'INITIALIZE
FONT AND SWITCH TO PAGE 1 CLEARED
SCREEN ,2 :'ENABLE EXT BKGND COLOR MODE
```
