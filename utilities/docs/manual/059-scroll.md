---
name: SCROLL
order: 59
token: auto
---


PURPOSE:

To move a section of text in a specified
direction with optional wrapping.

SYNTAX:
```text

SCROLL x1, y1 TO x2, y2 [,direction]
[,wrap]
```

DESCRIPTION:

SCROLL allows any section of text on the
screen to be scrolled up, down, left, or
right. The section is moved in the
specified direction by one character per
statement execution. SCROLL and SCREEN
statements can be used together in a
loop to achieve fine scrolling text. See
the example at the end of Appendix G.

x1 (0-39), y1 (0-24) define the
coordinates of the first character, on a
text screen, to scroll. This is the
upper left corner of the display that
will be scrolling.

x2 (0-39), y2 (0-24) define the
coordinates of the last character, on a
text screen, to scroll. This is the
lower right corner of the display that
will be scrolling.

direction (0-3, default 0) defines the
direction of scroll as follows:

DIRECTION MOVEMENT
0 up (default)
1 down
2 left
3 right

wrap (0=truncate, 1=wrap, default 0)
specifies what happens to the text that
is scrolled off the screen. Wrapping
copies such text to the opposite side
while truncating writes spaces to the
opposite side.

NOTE: SCROLL moves physical screen lines
only. The editor’s screen line link
table is not adjusted after scrolling up
or down. Any logical line that consists
of two physical lines will skew the
alignment. You can, however, invoke the
editor’s scroll up subroutine (without
wrapping) with a directly call to it
using SYS $E8EA.

EXAMPLE:
```text

SCROLL 0,0 TO 39,0,3 :'SCROLL TOP LINE
RIGHT, WITH WRAPPING
```
