---
name: ERR (statement)
order: 19
token: auto
---


PURPOSE:

To invoke an error during program
execution, clear the last error state or
turn off error trapping enabled by the
ON ERR GOTO statement.

SYNTAX:
```text

ERR err#
ERR CLR | OFF
```

DESCRIPTION:

The ERR statement is used to invoke an
error or control error trapping. A well
designed program should have an error
handler subroutine that can attempt to
fix the problem with or without help
from the user, then resume program
execution accordingly. Once an error
handler is enabled using the ON ERR GOTO
line statement, any error will cause the
program to GOTO the specified line.

A program can determine its own error
condition and manually invoke any
standard error (1-36) or a user-defined
error (0, 37-127). A user-defined error
is specific to the running program and
can have any mean defined by the
programmer. The error handler subroutine
can determine which error occurred using
the ERR variable and proceed
accordingly.

err# (0-127) is the error number to
invoke. Error numbers 1-30 are the CBM
BASIC errors. Error numbers 31-36 are
MDBASIC errors while 0 and 37-127 are
user-defined. Any attempt to raise an
error outside the valid range will
always result in error 14 (Illegal
Quantity). See appendix B for more
details.

ERR OFF disables error trapping if
enabled (See the ON ERR GOTO statement).

ERR CLR clears the info from the last
error setting ERR=0, ERRL=65535.

EXAMPLE:
```text

10 ON ERR RESUME NEXT: PRINT"HERE WE GO"
20 ERR 28 :'INVOKE VERIFY ERROR
30 IF ERRL > -1 THEN PRINT "LAST
ERROR#:";ERR;" LINE#:";ERRL
40 ERR CLR : PRINT"ERROR STATE CLEARED"
```
