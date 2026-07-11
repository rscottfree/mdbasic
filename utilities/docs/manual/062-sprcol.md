---
name: SPRCOL
order: 62
token: auto
---


PURPOSE:

To select a multicolor mode and set
colors used by the foreground text,
background text or any sprite that has
multicolor mode enabled.

SYNTAX:
```text

SPRCOL [sc1] [,sc2] [,colorModeFlags]
```

DESCRIPTION:

SPRCOL selects colors for sprites having
multicolor mode enabled. Colors sc1 &
sc2 define two additional colors that
that can occupy the same 24 x 21 sprite.
All sprites in multicolor mode will
share these extended colors. The table
below lists the four 2-bit patterns with
the source of the color value:

| PATTERN | COLOR |
|--|--|
| 00 | background color |
| 01 | sc1 |
| 10 | sprite color |
| 11 | sc2 |

On system startup the default colors are
sc1=4 (Purple) and sc2=0 (Black). To be
able to see all the colors it is
important to set the screen’s background
color to a different color than the
colors selected.

colorModeFlags is an 8-bit value
representing the eight available
sprites. The bits are used as flags to
turn on or off multicolor mode for each
sprite. Multicolor mode can be
individually enabled for a specific
sprite using the SPRITE statement. This
parameter offers an alternative to
select the color mode for all eight
sprites in one statement.

Designing a multicolor sprite is similar
to designing a multicolor character when
arranging bit-pairs to select the
corresponding color (See DESIGN
statement).

EXAMPLE:
```text

SPRCOL 5,6 :'SELECTS COLORS FOR ALL
SPRITES WITH MULTICOLOR MODE ENABLED
SPRCOL 1,2,255 :'SELECTS COLORS AND
ENABLES MULTICOLOR MODE FOR ALL SPRITES
SPRCOL ,,0 :'TURN OFF MULTICOLOR MODE
FOR ALL SPRITES
```
