---
name: APPENDIX B: ERRORS
order: 78
token: none
---

ERROR CODES & MESSAGES
Error numbers 1-30 are the CBM BASIC
errors. Error numbers 31-36 are MDBASIC
errors, while 0 and 37-127 are
user-defined. A user-defined error is
defined by the programmer and invoked
manually using the ERR statement. A
custom error handler is declared using
the ON ERR GOTO statement. The standard
error handler will stop the program and
display the error message (see chart
below).

To manually invoke an error use the ERR
statement followed by the error number.
Any attempt to raise an error outside
the valid range will always result in
error 14 (ILLEGAL QUANTITY).

| NUMBER | ERROR MESSAGE |
|--|--|
| 0 | USER DEFINED |
| 1 | TOO MANY FILES |
| 2 | FILE OPEN |
| 3 | FILE NOT OPEN |
| 4 | FILE NOT FOUND |
| 5 | DEVICE NOT PRESENT |
| 6 | NOT INPUT FILE |
| 7 | NOT OUTPUT FILE |
| 8 | MISSING FILENAME |
| 9 | ILLEGAL DEVICE NUMBER |
| 10 | NEXT WITHOUT FOR |
| 11 | SYNTAX |
| 12 | RETURN WITHOUT GOSUB |
| 13 | OUT OF DATA |
| 14 | ILLEGAL QUANTITY |
| 15 | OVERFLOW |
| 16 | OUT OF MEMORY |
| 17 | UNDEF'D STATEMENT |
| 18 | BAD SUBSCRIPT |
| 19 | REDIM'D ARRAY |
| 20 | DIVISION BY ZERO |
| 21 | ILLEGAL DIRECT |
| 22 | TYPE MISMATCH |
| 23 | STRING TOO LONG |
| 24 | FILE DATA |
| 25 | FORMULA TOO COMPLEX |
| 26 | CAN'T CONTINUE |
| 27 | UNDEF'D FUNCTION |
| 28 | VERIFY |
| 29 | LOAD |
| 30 | BREAK |
| 31 | MISSING OPERAND |
| 32 | ILLEGAL VOICE NUMBER |
| 33 | ILLEGAL SPRITE NUMBER |
| 34 | ILLEGAL COORDINATE |
| 35 | RESUME WITHOUT ERR |
| 36 | STACK OVERFLOW |
| 37-127 | USER DEFINED |

Some errors are more critical than
others and may need special handling to
be able to resume the program. For
example, after a STACK OVERFLOW error,
all GOSUB and FOR statements lose their
context and thus can no longer use the
RETURN and NEXT statements. Therefore
the error handler would have to resume
to a specific place in the program
outside this context. An OUT OF MEMORY
error is also very bad since the system
already tried to free up some memory
(using string garbage collection) before
invoking this error. Therefore,
additional steps would be needed to free
up memory, like clearing all variables
with the CLR statement.

Some errors are a result of a poorly
designed program and flawed logic (2, 3,
6,
7, 9, 10, 11, 12, 13, 17, 18, 19, 22,
25, 27, 31-35). Some errors are due to
the lack of validation and careful
computation (1, 8, 14, 15, 20, 23). Some
are specific to immediate mode and can
only occur in a running program if
manually invoked using the ERR statement
(21, 26).

To avoid a BREAK error, use the
statement STOP KEY OFF. When the STOP
key is pressed the ASCII value of 3 will
appear in the keyboard buffer rather
than stopping the program.
