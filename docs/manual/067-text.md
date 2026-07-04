---
name: TEXT
order: 67
token: auto
---


PURPOSE:

To print characters on a bitmap screen
or to reset the display to the standard
text and color modes.

SYNTAX:
```text

TEXT
TEXT x, y, string$ [,charset] [,sx]
[,sy] [,plottype] [,color]
```

DESCRIPTION:

TEXT is a dual purpose statement. When
used with no parameters the SCREEN is
turned ON (visible) and set to page 0
for standard text, font and color mode.
TEXT with parameters will print
characters anywhere on a bitmap screen
with varying sizes and character sets.

x (0-319 hires, 0-159 multicolor), y
(0-199) are the bitmap coordinates where
the top left-hand corner of the first
character will print. The last plotted
point can be referenced with x=INF(20)
and y=INF(19).

string$ is the string of characters to
be printed on the bitmap screen. There
are 29 ASCII control characters
supported. Insert is not supported. Any
string that does not fit on the screen
will be truncated (no wrapping).

charset (0-3) is the character set to
use when printing the letters or
symbols.

| CHARSET | DESCRIPTION |
|--|--|
| 0 | Upper-case and symbols (default) |
| 1 | Reverse of set 0 |
| 2 | Lower-case and symbols |
| 3 | Reverse of set 2 |

sx, sy (0-31, default 1) select the size
of the x and y dimensions. The numbers
here are multiples of the normal size.
In multicolor mode the text clarity will
be reduced and can be corrected by
setting sx = 2.

plottype (0-3) is how the characters
will be printed (see PLOT statement).

color (0-15 hires, 1-3 multicolor) is
the text color (See MAPCOL statement).

EXAMPLE:
```text

TEXT :'RETURN TO STANDARD TEXT, FONT AND
COLOR MODE
TEXT 0,0,"CBM",0,1,5 :'UPPER CHARS AT
TOP LEFT CORNER WITH TALL LETTERS
TEXT INF(20),INF(19)," BASIC",1 :'RVS
CHARS AT CURRENT LOCATION DEFAULT SIZE
```
