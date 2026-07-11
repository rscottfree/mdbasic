---
name: MAPCOL
order: 34
token: auto
---


PURPOSE:

To set the default colors to be used
when plotting dots on a bitmap screen.

SYNTAX:
```text

MAPCOL [c1], [,c2] [,c3] [,c4]
```

DESCRIPTION:

MAPCOL is used with bitmap graphics for
selecting the colors to be used when
plotting dots. The next plotted dot by
any graphics statements will use the
newly applied setting. Refer to the
COLOR statement for a list of the
available colors.

c1 (0-15) changes the default color for
plotting dots. In multicolor mode this
is the dot color for bit pattern 01.

c2 (0-15) changes the default background
color of the 8 x 8 square that contains
the hires dot. In multicolor mode this
is the dot color for bit pattern 10.

c3 (0-15) is only used in multicolor
mode to set the color for bit pattern
11.

c4 (0-15) is only used in multicolor
mode to set the color for bit pattern
00. This is the same color used by the
text background.

In hires mode, every 8 x 8 square can
only have one color of plotted dots.
When mixing colors on a hires screen,
each set of 64 dots must be the same
color. This a limitation of the VIC-II
chip.

In multicolor mode the horizontal
resolution is cut in half to support 3
different pixel colors in the same 8 x 8
square. When in this mode, all graphics
statements that select a color will use
values 1, 2 or 3 corresponding to c1, c2
and c3 respectively using the following
bit patterns:

| COLOR | PATTERN | DESCRIPTION |
|--|--|--|
| c1 | 01 | Upper nybble of scan code in Video Matrix ($C800-$CBE8) |
| c2 | 10 | Lower nybble of scan code in Video Matrix ($C800-$CBE8) |
| c3 | 11 | Lower nybble of Color RAM in Video Matrix ($D800-$DBE8) |
| c4 | 00 | Background Color Register 0 BGCOL0 ($D021) |

EXAMPLE:
```text

MAPCOL 1,2 :'CHANGES C1 AND C2 ONLY
```
