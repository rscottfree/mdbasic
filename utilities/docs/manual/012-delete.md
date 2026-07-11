---
name: DELETE
order: 12
token: auto
---


PURPOSE:

To remove a line or range of consecutive
lines from a program.

SYNTAX:
```text

DELETE
DELETE line
DELETE line1-line2
DELETE line1-
DELETE -line2
```

DESCRIPTION:

DELETE aids the programmer when editing
a program. Any line or groups of lines
may be removed from the program rapidly.
Specifying the line numbers to delete is
exactly like specifying the lines to
display when using the LIST command.

DELETE with no parameters is the same
executing the NEW command.

line is a single line number to delete
from the program.

line1 is the first line to be deleted in
a range. This value may be omitted if
the first line to delete is the first
line in the program. A dash would follow
the number to indicate a range.

line2 is the last line to be deleted in
a range. This value may be omitted if
the last line to delete is the last line
in the program. A dash must always
precede this value to indicate a range.

DELETE will not cause an error if the
specified line numbers to delete do not
exist. If executed in a running program
then the program will end.

EXAMPLE:
```text

DELETE 40        :'DELETES LINE 40
DELETE :'DELETES THE ENTIRE PROGRAM
DELETE 150-199 :'DELETES LINES 150 TO
199
DELETE -100 :'DELETES LINES 0 TO 100
```
