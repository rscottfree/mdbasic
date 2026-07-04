---
name: COLOR
order: 10
token: auto
---


PURPOSE:

To select the foreground, background and
border colors.

SYNTAX:
```text

COLOR [foreground] [,background]
[,border] [,bgcol1] [,bgcol2] [,bgcol3]
```

DESCRIPTION:

The COLOR statement is used to select
three different color settings for the
text screen. Parameters can be omitted
to avoid changing the current setting.

foreground (0-15) sets the text color
for subsequent PRINT statements.

background (0-15) sets the background
color for text and multi-color bitmap
screens.

border (0-15) sets the screen border
color.

bgcol1, bgcol2 determine the colors used
in both multicolor and extended
background color text modes. bgcol3 is
only for extended background color mode.
For more details on these color modes,
refer to the SCREEN statement.

The following is a table of available
colors and their associated number:

| VALUE | COLOR | VALUE | COLOR |
|--|--|--|--|
| 0 | Black | 8 | Orange |
| 1 | White | 9 | Brown |
| 2 | Red | 10 | Light Red |
| 3 | Cyan | 11 | Gray 1 (Dark) |
| 4 | Purple | 12 | Gray 2 (Medium) |
| 5 | Green | 13 | Light Green |
| 6 | Blue | 14 | Light Blue |
| 7 | Yellow | 15 | Gray 3 (Light) |

EXAMPLE:
```text

COLOR 14,6,14 :'SET COMMODORE STANDARD
COLOR SCHEME
COLOR ,0 :'SET BACKGROUND COLOR TO BLACK
COLOR 2 :'SELECT RED AS THE COLOR FOR
THE NEXT PRINT
```
