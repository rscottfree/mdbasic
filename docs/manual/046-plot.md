---
name: PLOT
order: 46
token: auto
---


PURPOSE:

To turn a pixel on or off on a bitmap
screen.

SYNTAX:
```text

PLOT x, y [,plotType] [,color]
```

DESCRIPTION:

The PLOT statement is used to change an
individual pixel’s state and color. It
can set, clear or flip the pixel’s
on/off state at a specified coordinate.
It can also be used to simply set the
current plot coordinates without any
change to the pixel. This is useful when
using the DRAW statement.

x (0-319), y (0-199) in hi-resolution
mode, x (0-159), y (0-99) in multicolor
mode. x, y are the coordinates
referencing a pixel on a bitmap screen.
Any values out of range in the mode
selected will result in an ILLEGAL
COORDINATE ERROR.

plotType (0-3) determines how the dot
will be plotted as follows:

PLOT TYPE FUNCTION
0 Erase pixel
1 Plot pixel (default)
2 Flip pixel (on=off, off=on)
3 None, set current plot coordinate only
– useful with DRAW statement

color (0-15 in hi-resolution mode, 1-3
in multicolor mode), sets the color for
the pixel. See the MAPCOL statement for
a list of the available colors for both
modes.

EXAMPLE:
```text

PLOT 160,100 :'PLOT CENTER OF HIRES
SCREEN
PLOT 80,50,1,1 :'PLOT CENTER OF
MULTICOLOR SCREEN WITH WHITE DOT
PLOT 0,0,0 :'TURN OFF PIXEL IN TOP LEFT
CORNER
PLOT 319,199,2 :'FLIP BOTTOM RIGHT
CORNER PIXEL'S CONDITION
```
