---
name: ON ERR
order: 40
token: auto
---


PURPOSE:

To enable and define the global error
handling scheme to either ignore errors
or use a custom error handling
subroutine.

SYNTAX:
```text

ON ERR GOTO lineNum
ON ERR RESUME NEXT
[ON] ERR OFF
```

DESCRIPTION:

ON ERR GOTO enables redirection of
program execution to a specified line
number when an error occurs. This is
useful to avoid sudden program
termination when a file or device issue
occurs. A custom error handler can try
to fix the problem or prompt the user to
help resolve the issue, then resume as
needed.

lineNum is the line number that the
program will GOTO when an error occurs.
An invalid lineNum will result in an
UNDEF'D STATEMENT ERROR.

ON ERR RESUME NEXT will ignore all
errors and skip to the next statement.
The variables ERR and ERRL can be used
to get the error number and line number.
To clear the last error information use
the statement ERR CLR.

ON ERR OFF, or simply ERR OFF is used to
switch back to the standard BASIC error
handler and clear the last error
information. Errors will stop the
program.

E = ERR returns the number of the error
that occurred. This can be used to
decode which error occurred and handle
it appropriately. See Appendix B.

E = ERRL returns the line number that
the error occurred.

RESUME is the only statement used to
exit a custom error handling subroutine.
Error trapping is automatically paused
until a RESUME statement is executed. If
an error occurs before a RESUME
statement is executed then the program
will stop and the error message is
displayed. This is to avoid continuously
restarting the subroutine forever. After
a RESUME statement is executed the
previous error number and line number
are cleared (ERR CLR) and the error
trapping resumes.

EXAMPLE:
```text

10 ON ERR RESUME NEXT :'IGNORE ALL
ERRORS
20 PRINT 10/INT(RND(-TI)*10) :'POSSIBLE
DIVIDE BY ZERO
30 IF ERR > 0 THEN PRINT"ERROR
OCCURRED":END :ELSE GOTO20
```
