---
name: RESTORE
order: 52
token: auto
---


PURPOSE:

To reset the data pointer to either the
first or specific data statement.

SYNTAX:
```text

RESTORE
RESTORE [lineNum]
```

DESCRIPTION:

RESTORE is an existing CBM BASIC
statement which resets the data pointer
to the first data line in the program.
It has been augmented to support
restoring to an optionally specified
line number in the program.

When all DATA in a program has been
consumed by the READ statement, any
attempt to READ more data will cause an
OUT OF DATA ERROR. RESTORE allows
re-reading of data at any time, at any
DATA statement, as many times as
necessary.

RESTORE without a line number will set
the next READ to the first DATA
statement in the program. No error
occurs if the BASIC program does not
contain any DATA statements. This is the
CBM BASIC implementation.

RESTORE lineNum will set the line number
for the next READ statement to get its
DATA. If lineNum is not a valid line
number in the program, an UNDEF'D
STATEMENT ERROR will occur. If lineNum
does not have a DATA statement, the next
READ statement will search from that
point to the end of the program for the
next DATA line. If no DATA line is
found, then the next READ statement will
cause an OUT OF DATA ERROR.

EXAMPLE:
```text

RESTORE :'SETS DATA POINTER AT FIRST
LINE IN PROGRAM
RESTORE 100 :'DATA IS FOUND STARTING AT
LINE 100
```
