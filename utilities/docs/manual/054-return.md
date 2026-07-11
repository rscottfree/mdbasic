---
name: RETURN
order: 54
token: auto
---


PURPOSE:

To return from a subroutine called by
the GOSUB statement.

SYNTAX:
```text

RETURN
RETURN [lineNum]
```

DESCRIPTION:

RETURN is a CBM BASIC statement used to
return to the statement after the GOSUB
statement that called the function. It
has been augmented by MDBASIC to allow
the safe redirection of the program to a
specified line number instead of the
statement that followed the GOSUB
statement that made the call.

RETURN without a line number returns to
the statement following the GOSUB
statement that made the call. This is
the standard CBM-BASIC behavior.

RETURN lineNum will abort the GOSUB call
by discarding the five bytes of stack
information pertaining to the call then
perform a GOTO with the line number
provided. This is the MDBASIC
augmentation of the RETURN statement.

Returning to a different point in the
program breaks the rules of control-flow
programming, however, traditional BASIC
is not a control-flow language and is
dependent on line numbers on every line
of program text.

Using the RETURN statement without
previously executing a GOSUB statement
will cause RETURN WITHOUT GOSUB ERROR.

EXAMPLE:
```text

10 A=1: PRINT"THIS IS A TEST"
20 GOSUB 100:PRINT"RETURNED BACK"
25 PRINT"*********"
30 PRINT"DONE"
40 END
100 PRINT"*SUBROUTINE*"
110 IF A > 0 THEN RETURN30
120 RETURN
```
