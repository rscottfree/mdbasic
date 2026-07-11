---
name: LINE INPUT#
order: 33
token: auto
---


PURPOSE:

To input a line of characters from an
open file that is terminated by a
carriage return or end of file (EOF).

SYNTAX:
```text

LINE INPUT# fileNumber, A$ [,B$ [,C$ [,…
] ]]
```

DESCRIPTION:

LINE INPUT# is much like the INPUT#
statement, except LINE INPUT# is only
terminated by the carriage return
character (ASCII 13). This is useful for
reading text files that may contain
commas or semicolons.

fileNumber is the already opened logical
file number to read characters from
instead of the keyboard.

A$ is the variable that will store the
string of characters from the device
associated with the specified file
number. It is legal to supply multiple
strings (B$, C$,…,Z$) each separated by
a comma to capture multiple lines of
input consecutively.

The text file is read starting from the
current position to the next carriage
return character, end of file (EOF) or
the length of the string reaches 255
characters.

Be sure to trigger a garbage collection
manually when reading large files. This
can be done by using the statement
SYS46374 or the function FRE(0). This
approach will ensure that a large amount
of discarded strings will not pile up
thus avoiding a long-running garbage
collection process.

EXAMPLE:
```text

10 '***READ FROM FILE***
15 DIM A$,L,C
20 OPEN 1,8,0, "MYFILE.SEQ"
30 LINE INPUT#1, A$
40 PRINT A$
45 L=L+1:C=C+LEN(A$)
50 IF ST AND 64 GOTO 70
60 SYS46374:GOTO 30
70 CLOSE 1
80 PRINT L;"LINES,";C;"CHARACTERS."
90 END
```
