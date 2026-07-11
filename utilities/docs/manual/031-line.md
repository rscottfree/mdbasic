---
name: LINE
order: 31
token: auto
---


PURPOSE:

To draw a line between two selected
points on a bitmap screen.

SYNTAX:
```text

LINE x1, y1 TO x2, y2, [plotType],
[color]
```

DESCRIPTION:

x1 & y1 define the start point to begin
drawing the line.

x2 & y2 define the end point of where
the line ends.

The values for both sets of points are
limited and based on the color mode. In
hires mode x1 and x2 (0-319), y1 and y2
(0-199). In multicolor mode x1 and x2
(0-159), y1 and y2 (0-99). Specifying a
point outside the range of the current
color mode will result in an ILLEGAL
COORDINATE ERROR.

plotType (0-3) determines how the line
will be plotted. 0=dots off, 1=dots on,
2=flip pixel (on=off, off=on), 3=none
(set plot location).

color (0-15 in hi-resolution mode, 1-3
in multicolor mode), is an optional
parameter to select the paint color. If
omitted then the last color selected by
any graphics statement will be used.
Refer to the MAPCOL statement for
details about the available colors for
both hires and multicolor bitmap modes.
Refer to the COLOR statement for a list
of available colors.

EXAMPLE:
```text

LINE 0,0 TO 319,199 :'DRAWS DIAGONAL
LINE ACROSS SCREEN
LINE 160,100 TO 0,199,2 :'FLIPS LINE OF
DOTS FROM CENTER TO LOWER LEFT
```
