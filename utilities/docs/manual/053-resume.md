---
name: RESUME
order: 53
token: auto
---


PURPOSE:

To return from a custom error handling
subroutine that was previously defined
by the last ON ERR GOTO statement and
after which an error occurred.

SYNTAX:
```text

RESUME
RESUME NEXT
RESUME [lineNum]
```

DESCRIPTION:

RESUME is used in conjunction with the
ON ERR GOTO statement to return from a
custom error handling subroutine. The
location to return is described below.

RESUME with no parameters will return
program execution to the statement that
caused the error. This is used to retry
the failed statement.

RESUME NEXT returns execution to the
statement immediately following the
statement that caused the error.

RESUME lineNum redirects the program
execution to any line in the program.
Resuming to an invalid lineNum will
cause an UNDEF'D STATEMENT ERROR.

Regardless of how resuming is done, the
previous error number is set to 0 and
the previous error line number is set to
65535 (ERR CLR) since it was handled.

Error trapping is paused automatically
when entering the error handling
subroutine to avoid a continuous call to
the subroutine which would eventually
lead to a STACK OVERFLOW ERROR. RESUME
will re-enable the last used error
handling definition set by ON ERR GOTO
line#. Therefore, it is possible to nest
multiple error handlers by carefully
setting & resetting the definition.

If RESUME is executed without a custom
error handler being invoked by an error,
then RESUME WITHOUT ERR ERROR will
occur. All error handler subroutines
should never be manually entered (GOTO,
GOSUB) and always exit with a RESUME
statement.

EXAMPLE:
```text

10 ON ERR GOTO 1000
…(main program here)…
999 END
1000 PRINT"ERR:";ERR;"LINE:";ERRL
1001 RESUME NEXT :'SKIP OVER STATEMENT
THAT CAUSED THE ERROR
```
