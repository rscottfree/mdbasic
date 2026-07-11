---
name: DESIGN
order: 13
token: auto
---


PURPOSE:

To redefine a character's shape for use
on screen pages 1 to 4.

SYNTAX:
```text

DESIGN NEW
DESIGN screenCode, charset, d0, d1, d2,
d3, d4, d5, d6, d7
```

DESCRIPTION:

Each character is formed by an 8 x 8
grid of dots, where each dot can be on
or off. The data is stored in 8 bytes.
The bits that make up each byte will
decide what the character looks like. An
example of the letter A is shown below:

```text
IMAGE     BINARY    DATA
...**...  00011000  24
..****..  00111100  60
.**..**.  01100110  102
.******.  01111110  126
.**..**.  01100110  102
.**..**.  01100110  102
.**..**.  01100110  102
........  00000000  0
(*=bit on .=bit off)
```

DESIGN NEW copies all four character
sets available in the Commodore 64 ROM.
This allows use of the existing
character designs while only applying
changes to a select few.

Redefined characters are only visible
when viewing SCREEN pages 1 to 4,
however, new character designs can be
applied while viewing any page and are
available immediately. If the page has
not been displayed since the computer
was powered- up then it will contain
random text Therefore it is necessary to
clear the screen (SCREEN CLR) when
switching pages for the first time.

Screen memory and sprite pointers reside
together in blocks of 1K RAM based on
which page is selected. Switching pages
when sprites are visible will result in
the loss of the image data. To avoid
this copy the image data to the
available RAM area that is compatible
with the selected page. Use the SPRITE
statement to adjust the pointers or just
turn off all sprites (SPRITE OFF).

Use the SCREEN statement to select a
page for viewing. Pages 1-4 can only
support 48 sprite images loaded at one
time. All pages share the same color
RAM. The table below outlines memory
usage for each page.

<!-- table: mode=sections -->
| PAGE | SCREEN RAM | SPRITE POINTERS | AVAILABLE IMAGE RAM | SPRITE DATA INDEXES |
|--|--|--|--|--|
| 0 | $0400-$07E7 | $07F7-$07FF | $0340-$03FF, $0800-$3FBF | 13-15,32-255 |
| 1 | $C000-$C3E7 | $C3F7-$C3FF | $C400-$CFFF | 16-63 |
| 2 | $C400-$C7E7 | $C7F7-$C7FF | $C000-$C3FF, $C800-$CFFF | 0-15, 32-63 |
| 3 | $C800-$CBE7 | $CBF7-$CBFF | $C000-$C7FF, $CC00-$CFFF | 0-31, 48-63 |
| 4 | $CC00-$CFE7 | $CFF7-$CFFF | $C000-$CBBF | 0-47 |

NOTE: Page 3 is used by the bitmap
screen. Page 4 is used by the RS-232 I/O
buffers. Using SERIAL operations on page
4 will result in the visual display of
these buffers. Also, machine language
subroutines may need to be relocated.

screenCode (0-255) selects which
character to redefine. Note that this is
not the ASCII code. The actual character
affected is based on the charset
selected.

charset (0-3) is the character set to
modify as listed in the table below:

| CHARSET | DESCRIPTION |
|--|--|
| 0 | Upper-case and symbols |
| 1 | Reverse of set 0 |
| 2 | Lower-case and symbols |
| 3 | Reverse of set 2 |

d0,d1,d2,d3,d4,d5,d6,d7 are the eight
data bytes that make up the shape of
each character. By using the percent
sign (%), the data can be represented as
binary numbers, making obtaining the
data simple. If any of the data is
omitted, a MISSING OPERAND ERROR will
result.

To save the entire redefined character
set use secondary device 17, example:

SAVE"MYDESIGN",8,17

To load a redefined character set use
secondary device 17, example:

LOAD"MYDESIGN",8,17

Saving and loading redefined character
sets can be done without being in design
mode. Saving without a definition will
result in a garbage character set. The
memory area for a redefined character
set overlaps the second 4K (bottom half)
of bitmap memory, thus only one mode can
be visible at a time. However this
overlap can be used to define a
multi-character image using commands for
a bitmap (DRAW, LINE, CIRCLE, etc.) then
save as a character set. Only dot data
would be saved; color is not included
and would have to be applied when
placing the redefined characters on a
text screen.

EXAMPLE:
```text

10 DESIGN NEW :'COPY ROM CHARS TO RAM
FOR INIT DESIGN
20 DESIGN 0,0, 0,0,0,8,8,0,0,0 :'SCAN
CODE 0 (CHARACTER @) CHANGES TO A DOT
30 SCREEN 2:SCREEN CLR :'SWITCH TO PAGE
2 AND CLEAR IT
40 PRINT"@ NOW ON PAGE 2 @" :'DISPLAY
DEMO OF NEW CHAR DESIGN
50 WAIT 240 :'WAIT 240 JIFFIES (4
SECONDS)
60 SCREEN 0 :'SWITCH BACK TO STANDARD
TEXT SCREEN
```
