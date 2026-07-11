---
name: SPRITE
order: 61
token: auto
---


PURPOSE:

To set/change the configuration of a
sprite including the visibility, color &
color mode, foreground priority, data
index and expansion size for the image.

SYNTAX:
```text

SPRITE spriteNum, [visible] [,color]
[,multi] [,index] [,priority] [,size]
SPRITE spriteNum EXPAND size
SPRITE spriteNum DATA index
SPRITE ON | OFF
SPRITE EXPAND size
```

DESCRIPTION:

A sprite is a Movable Object Block (MOB)
that is 24 bits wide and 21 bits tall
consuming 63 bytes of memory per shape.
Sprites have their own x & y coordinate
system which differs from that of the
bitmap screen. Any of the eight sprites
can be moved anywhere on the screen,
even under the border that surrounds the
edge of the screen. Image display is
hardware-driven so there is no need to
erase and draw the image when the
coordinates of a sprite changes. See the
MOVE statement for more details.

Each SPRITE parameter can be skipped to
target only the ones needing to change.
Parameters can also be omitted to end
the statement without specification.

spriteNum (0-7) selects the sprite that
is affected.

visible (0 or 1) is a Boolean expression
that turns the selected sprite on or
off. Any other value will result in an
ILLEGAL QUANTITY ERROR.

color (0-16) selects the color for the
sprite with 16 being a glow effect.

multi (0 or 1) is a Boolean expression
that selects the color mode (0=hires,
1=multicolor). If multicolor mode is
selected, more colors can be used in the
sprite, but the horizontal resolution is
cut in half to facilitate this feature.
Use the SPRCOL statement to set the
colors sc1 & sc2 used by all sprites.
The table below lists the four 2-bit
patterns and the associated color:

| PATTERN | COLOR |
|--|--|
| 00 | background color |
| 01 | sc1 |
| 10 | sprite color |
| 11 | sc2 |

Designing a multicolor sprite is the
same as a multicolor character when
arranging the bit-pairs for the
corresponding colors (See DESIGN
statement).

index (0-255) is the index of the
64-byte data block that defines the
shape of the sprite. The memory address
can be calculated by the formula:

ADDRESS=(INDEX*64)+(BANK*16384)

BANK (0-3) is the 16K VIC-II base video
memory bank. MDBASIC selects the memory
bank depending on the active graphics
mode selected.

<!-- table: mode=sections -->
| BANK | MDBASIC MODE | MEMORY RANGE | COMMENTS |
|--|--|--|--|
| 0 | Standard Text | 0-16383 | 1K SYS RAM, 1K VIDEO RAM, 14K BASIC RAM |
| 1 | n/a | 16834-32767 | 16K BASIC RAM |
| 2 | n/a, Restricted | 32768-49151 | 16K MDBASIC RAM, 8K CBM BASIC ROM |
| 3 | Bitmap Graphics & Custom Text | 49152-65535 | 4K HIRAM, 4K DEVICE RAM, 16K KERNAL ROM. 1K VIDEO RAM is at 51200-52223 |

priority (0 or 1) is a Boolean
expression that determines the priority
of the sprite graphics to foreground
graphics. When priority is set to 0
(default) the sprite will appear over
all bitmap graphics and text characters;
a value of 1 will make the sprite appear
underneath. If this operand is greater
than 1, an ILLEGAL QUANTITY ERROR will
result.

size (0 to 3) is the expansion sizing
options for the sprite. A sprite’s
horizontal and vertical dimensions can
be displayed twice the normal size. When
an axis is expanded, each pixel is drawn
twice along that axis, which increases
the size of the image. The table below
lists the possible values for this
parameter:

| SIZE | DESCRIPTION |
|--|--|
| 0 | Normal (no expansion) |
| 1 | Horizontal expansion only |
| 2 | Vertical expansion only |
| 3 | Horizontal and vertical expansion |

Below is a list of alternate syntax for
setting sprite parameters:

1. Setting only the size parameter:
SPRITE spriteNum,,,,,,size
SPRITE spriteNum EXPAND size

2. Setting only the image index
parameter:
SPRITE spriteNum,,,,index
SPRITE spriteNum DATA index

3. Setting only the visible parameter
for all sprites:
SPRITE ON
SPRITE OFF

4. Setting only the expansion size
parameter for all sprites:
SPRITE EXPAND size

To design a sprite shape you need 63
bytes of data which is placed into
memory starting at the address
calculated using the formula described
above. The data can be entered in DATA
statements or loaded from a file.

MDBASIC comes with a sprite editor that
is easy to use and will help develop the
sprite shape needed in hires or
multicolor mode. The following is an
example of how a hires sprite is made
and turned into data:

```text
BINARY CODE               DATA
000011111111111111000000  15,255,192
001111111111111111110000  63,255,240
001111111111111111110000  63,255,240
011111000000000011111000  124,0,248
011100001000010000111000  112,132,56
111100011000011000111100  241,134,60
111100000000000000111100  240,0,60
111000000011000000011100  224,48,28
111000000011000000011110  224,48,30
111001100000000110011110  230,1,158
111000110000001100011110  227,3,30
111000011111111000011110  225,254,30
111100000000000000111110  240,0,62
111110000000000000111110  248,0,62
111111100000000011111110  254,0,254
111111110000000111111110  255,1,254
111111110000000111111100  255,1,252
111111110000000111111100  255,1,252
110000000000000000000110  192,0,6
100000000000000000000001  128,0,1
100000000000000000000001  128,0,1
```

Every three bytes makes one line of
pixels. There are 21 lines in a sprite
totaling 63 bytes. The data can easily
be put into DATA statements or a
sequential file for a loop to READ and
POKE them into memory.

Since sprite memory is represented in
64-byte blocks you will need to add an
additional byte to the end of your data
if you have multiple consecutive images.
This unused byte could be use to hold
additional data about the sprite. For
example, the color (4 bits), horizontal
& vertical expansion (2 bits),
visibility (1 bit) and priority (1 bit)
could all be encoded the bits of the
64th byte which you can apply to the
image after loading or reading the data.

EXAMPLE:
```text

SPRITE 0,1,7,0,13 :'SPRITE 0 ON, YELLOW,
NO MULTICOLOR, DATA POINTER 13
SPRITE 0,,,,14 :'CHANGE SPRITE 0'S
POINTER TO 14
SPRITE 0 DATA 14 :'SAME AS ABOVE WITH
ALT SYNTAX
SPRITE 1,,,,,,3 :'CHANGE SPRITE 1’S SIZE
TO EXPAND WIDTH AND HEIGHT
SPRITE 1 EXPAND 3 :'SAME AS ABOVE WITH
ALT SYNTAX
SPRITE 2,,,,,1 :'CHANGE SPRITE 2’S
PRIORITY TO BE UNDER TEXT/GRAPHICS
SPRITE ON :'TURN ON ALL SPRITES
SPRITE OFF :'TURN OFF ALL SPRITES
SPRITE EXPAND 3 :'EXPAND ALL SPRITES
HORIZONTAL AND VERTICAL
```
