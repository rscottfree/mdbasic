---
name: MOVE
order: 37
token: auto
---


PURPOSE:

To position a sprite at a specified
location or animate movement from one
location to another at a specified
speed.

SYNTAX:
```text

MOVE spriteNum, [x], [y]
MOVE spriteNum, x1, y1 TO x2, y2,
[speed]
MOVE spriteNum TO x, y, [speed]
```

DESCRIPTION:

Any of the eight sprites can be
displayed anywhere on the screen or move
from one point to another at a selected
speed.

spriteNum (0-7) defines which sprite to
move.

x (0-511) & y (0-255) select the
coordinates for the sprites upper left
corner. The coordinates for sprites do
not align to bitmap coordinates. A
sprite can be placed off the visible
screen. To place a sprite at the
top-left corner of the visible screen
use coordinates x=24 and y=50.

A sprite can be placed at a specific
coordinate or move to a specified
coordinate from its current location at
a specified speed.

x1, y1 & x2, y2 allows a sprite to move
from point x1, y1 to point x2, y2. These
values have the same range as x and y
stated above. Any coordinate value that
exceeds the legal range will cause an
ILLEGAL COORDINATE ERROR.

speed (0-255) controls the movement
rate between points, with 0 being the
fastest. A `TO` move returns immediately;
the sprite is advanced by the IRQ while
the next BASIC statements execute. Up to
eight sprites may move at the same time.

EXAMPLE:
```text

MOVE 0,24 :'ONLY SET X COORDINATE OF
SPRITE 0 TO 24
MOVE 0,,100 :'ONLY SET Y COORDINATE OF
SPRITE 0 TO 100
MOVE 1,180,120 :'PUT SPRITE 1 AT CENTER
OF SCREEN
MOVE 0,24,50 TO 320,229 :'MOVES FROM
TOP-LEFT TO BOTTOM RIGHT FAST
MOVE 7 TO 180,100, 50 :'MOVES SPRITE 7
FROM CURRENT TO CENTER SCREEN
```
