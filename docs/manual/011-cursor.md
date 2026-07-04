---
name: CURSOR
order: 11
token: auto
---


PURPOSE:

To set the cursor’s visibility and
position (column and/or row) on the
screen.

SYNTAX:
```text

CURSOR [column] [,row]
CURSOR ON | OFF
CURSOR CLR
```

DESCRIPTION:

CURSOR is commonly used in conjunction
with the PRINT statement. It allows the
cursor to be placed anywhere on a text
screen using the video matrix coordinate
scheme. It can also be used to control
the visibility of the cursor.

column (0-39) represents the column the
cursor moves to. If column exceeds its
range, an ILLEGAL COORDINATE ERROR will
result. If omitted then the current
column is used.

row (0-24) represents the line the
cursor moves to. If row exceed its
range, an ILLEGAL COORDINATE ERROR will
result. If omitted then the current line
is used.

CURSOR ON | OFF controls the visibility
of the cursor while in program mode.

CURSOR CLR will clear the entire line at
the cursor’s current position. You can
use this to initialize a line for user
input or simply just to clear a specific
line by first setting the cursor line
then clear it.

EXAMPLE:
```text

CURSOR 0,0 :'MOVE CURSOR TO TOP RIGHT
CORNER (HOME)
CURSOR 15 :'MOVES CURSOR TO COLUMN 15 ON
CURRENT LINE
CURSOR ,10 :'MOVES CURSOR TO LINE 10 OF
CURRENT COLUMN
CURSOR CLR :'CLEAR THE LINE AT THE
CURRENT CURSOR POSITION
CURSOR ON :'MAKE CURSOR VISIBLE AT
CURRENT POSITION
CURSOR OFF :'HIDE THE CURSOR (NO
BLINKING)
```
