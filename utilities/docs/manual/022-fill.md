---
name: FILL
order: 22
token: auto
---


PURPOSE:

To fill a section on a text screen with
a selected character and/or color.

SYNTAX:
```text
FILL col1, row1 TO col2, row2 [,poke
code] [,color]
```

DESCRIPTION:

FILL is used to fill a text screen with
a particular character and/or color. A
typical application for this statement
would be to erase a section of text, or
change its color.

col1 & row1 define the upper left hand
corner to start the fill process.

col2 & row2 define the lower right hand
corner to end the fill process.

Text coordinates have the same range as
the CURSOR statement. x(0-39) y(0-24).
Any value outside this range will result
in an ILLEGAL COORDINATE ERROR.

poke code (0-255), AKA: scan code, is
the number that represents the character
that is to be displayed. The poke code
(scan code) is not the same as the ASCII
code. This operand can be skipped using
a comma in its place, enabling the color
to be filled only.

color (0-15) is the color that is to be
filled in the defined area of the
screen. If in multicolor bitmap mode the
color is selected using index values
1,2 or 3. See the PLOT statement for
details.

See Appendix C for a list of screen
codes. The full list is available in the
Commodore 64 Programmers Reference
Guide.

EXAMPLE:
```text
10 SCREEN 0,0 :'TEXT PAGE 0 WITH
STANDARD COLOR SCHEME
20 FILL 0,0 TO 39,0,,2 :'TOP TEXT LINE
CHANGES COLOR TO RED
30 FILL 0,24 TO 39,24,32 :'FILL BOTTOM
TEXT SCREEN WITH SPACES
40 FILL 10,10 TO 20,20,64 :'FILL CENTER
TEXT SCREEN WITH @ SYMBOL
```
