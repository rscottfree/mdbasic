---
name: AUTO
order: 6
token: auto
---


PURPOSE:

To automatically generate line numbers
with a specified increment while typing
in a program.

SYNTAX:
```text

AUTO
AUTO [increment]
AUTO ON | OFF
```

DESCRIPTION:

When entering BASIC program text, every
line must start with a line number. Each
line number physically follows the next
in numeric order but not necessarily by
the same increment. AUTO assists the
programmer by automatically displaying
the next line number that should follow
with a predetermined increment. The
cursor is positioned after the line
number so that BASIC statements can be
entered. If the enter key is pressed
with no statements on the line then
auto-numbering stops. Turn off auto line
numbering before editing existing lines
of code.

AUTO ON turns on auto-line numbering
with the last increment used (default
10).

AUTO OFF (or AUTO 0) turns off auto-line
numbering.

increment (0-1023) is an integer value
used to calculate the next line number
after the enter key is pressed and the
cursor is on a line of code. If this
parameter is omitted then the last used
increment (default 10) will be used. A
value of zero is the same as AUTO OFF
and will not be remembered as the last
used increment.

The programmer must type in the first
line number, or press the return key on
the current working line number for the
next line to be displayed below the
current line. This is not helpful for
editing existing lines of code since the
line numbers already exist. Turn off
auto line numbering before editing
existing code. A valid line number is
between 0 and 63999.

EXAMPLE:
```text

AUTO :'ENABLES AUTO-LINE NUMBERING USING
PREVIOUS INCREMENT (DEFAULT 10)
AUTO 100 :'ENABLES AUTO-LINE NUMBERING
WITH INCREMENTS OF 100
AUTO OFF    :'DISABLES AUTO-NUMBERING
AUTO 0      :'DISABLES AUTO-NUMBERING
```
