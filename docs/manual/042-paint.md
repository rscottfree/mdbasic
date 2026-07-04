---
name: PAINT
order: 42
token: auto
---


PURPOSE:

To fill in a specified area of a bitmap
screen with a specified color.

SYNTAX:
```text

PAINT x, y [,color]
PAINT x1, y1 TO x2, y2 [,plotType]
[,color]
```

DESCRIPTION:

PAINT is used to fill an area on a
bitmap screen (SCREEN 5) with plotted
pixels. The first syntax uses a painting
algorithm (flood fill) that plots pixels
inside boundaries made by other
contiguous pixels that are already
plotted. The painting begins at the
specified point and continues plotting
until the entire enclosed area is
filled. The area to be painted must be
entirely enclosed with pixels. Any
opening of even one pixel in size will
result in painting outside the intended
area.

x, y define the coordinates where the
filling in of an object on the screen
will begin. In hires mode the maximum
values are x=0-319, y=0-199, but in
multicolor mode, x=0-159, y=0-99. Any
values out of range in the mode selected
will result in an ILLEGAL COORDINATE
ERROR.

The second syntax paints all pixels
inside the rectangle defined by x1, y1
(top- left) and x2, y2 (bottom-right)
using the specified plotType (0-3:
0=erase dot,
1=plot dot, 2=toggle dot, 3=none).

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

As with all graphics statements, no
check is made to ensure the current
screen is a bitmap screen. This allows
making changes to the bitmap without
being observed by the user. Showing the
bitmap can be done using the SCREEN
statement.

EXAMPLE:
```text

0 COLOR ,0,0 :'SET BORDER AND BACKGROUND
COLORS
10 MAPCOL 1,5,7 :'SET MULTICOLOR BITMAP
COLORS
20 SCREEN CLR 5,1 :'SHOW MULTICOLOR
BITMAP AND CLEAR IT
30 CIRCLE 160,100,30,30,,1,2 :'DRAW A
GREEN CIRCLE
40 PAINT 160,100,3 :'PAINT CIRCLE YELLOW
STARTING AT CENTER
```
