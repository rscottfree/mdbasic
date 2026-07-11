---
name: DRAW
order: 15
token: auto
---


PURPOSE:

To draw intricate shapes on a bitmap
screen.

SYNTAX:
```text

DRAW shape$
```

DESCRIPTION:

DRAW is used when drawing a picture that
has an intricate shape.

The PLOT statement can be used to set
the start point, the plot type, and the
color of the shape that will be drawn.
DRAW always draws from the last plotted
point using the last used color & plot
type.

shape$ contains the drawing commands
separated by commas. Each command has an
associated value. Below is the list of
available commands:

<!-- table: mode=sections -->
| COMMAND | FUNCTION | VALUE/RANGE |
|--|--|--|
| P | Change plot type | 0=clear, 1=set, 2=flip, 3=none |
| C | Change plot color | 0-15 |
| U | UP | 0-65535 |
| D | DOWN | 0-65535 |
| L | LEFT | 0-65535 |
| R | RIGHT | 0-65535 |
| E | UP & LEFT | 0-65535 |
| F | UP & RIGHT | 0-65535 |
| G | DOWN & LEFT | 0-65535 |
| H | DOWN & RIGHT | 0-65535 |

The values for directional draw commands
specify the number of dots (pixels) to
draw in the selected direction. If draw
reaches the end of the plot area then
wrap-around will occur.

To draw without plotting (like lifting
the pencil) use plot type 3. This will
simply move the current plot
coordinates. You will have to set the
plot type back to the original value to
continue plotting dots.

EXAMPLE:
```text

PLOT 10, 10 :'SET CURRENT COORDINATES
FOR DRAW
DRAW "C2,R30,P3,R30,P1,R30,D25,L90,U25"
:'RED BOX WITH OPEN TOP
```
