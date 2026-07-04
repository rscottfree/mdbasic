---
name: CIRCLE
order: 7
token: auto
---


PURPOSE:

To draw circles or ellipsoids on a
bitmap screen.

SYNTAX:
```text

CIRCLE x, y, xr, yr [,options]
[,plotType] [,color]
```

DESCRIPTION:

x & y are the coordinates for the center
of the circle to be drawn. (x=0-319 :
y=0-199) hi-res mode; (x=0-159 : y=0-99)
multicolor mode. Any values out of range
in the mode selected will result in an
ILLEGAL COORDINATE ERROR.

xr & yr (1-127) define the size of the x
radius and y radius. This is the
distance from the center point to the
outer edge of the circle. Many different
ellipsoids can be drawn by varying these
values. Values outside this range will
cause an ILLEGAL QUANTITY ERROR.

options (0-255, default 15) is an
optional set of eight bit flags:
Bit# Value Option
0 1 (default) Draw quadrant 1
(top-right)
1 2 (default) Draw quadrant 2 (top-left)
2 4 (default) Draw quadrant 3
(bottom-left)
3 8 (default) Draw quadrant 4
(bottom-right)
4 16 Draw line segment from center to
right edge
5 32 Draw line segment from center to
top edge
6 64 Draw line segment from center to
left edge
7 128 Draw line segment from center to
bottom edge

plotType (0-2) is the manner that the
dots will be drawn as follows:
0 = Erase dot(s)
1 = Draw dot(s)
2 = Flip dot(s) (reverses current
condition: on=off, off=on)
3 = None (useful with the DRAW
statement)

color (0-15 in hi-resolution mode, 1-3
in multicolor mode), is an optional
parameter to select the pixel color. If
omitted then the last color selected by
any graphics statement will be used.
Refer to the MAPCOL statement for
details about the available colors for
both hires and multicolor bitmap modes.
Refer to the COLOR statement for a list
of available colors

EXAMPLE:
```text

CIRCLE 159,99,50,40,%11111111,1,2 :'DRAW
RED CIRCLE WITH ALL OPTIONS
```
