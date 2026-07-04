---
name: ERR and ERRL (variables)
order: 20
token: auto
---


PURPOSE:

To return information about the last
error that was trapped.

SYNTAX:
```text

EN = ERR
EL = ERRL
```

DESCRIPTION:

These variables hold information about
the last error that occurred. These
variables are commonly used in
conjunction the ON ERR GOTO statement.
When an error occurs during program
execution these variables can be
interrogated to handle the error based
on which one it was and where in the
program that it occurred. Refer to the
ERR and ON ERR statements details on how
to add error handling to a program.

ERR is the error number of the most
recent error. If no error occurred then
the value is 0 (default). See Appendix B
for a complete list of error numbers.

ERRL is the line number of statement
that caused the most recent error. If no
error occurred or if the error occurred
in immediate mode then the value is
65535 (default) which is not a valid
line number.

These variables can be manually cleared
(reset to default) using the ERR CLR
statement. This will set the default
values as ERR = 0 and ERRL = 65535.

EXAMPLE:
```text

ON ERR GOTO 1000 :'IF ANY ERRORS OCCUR,
GOTO LINE 1000
.
.(main program goes here)
.
1000 PRINT ERR     :'PRINT ERROR NUM
1010 RESUME NEXT :'IGNORE ALL ERRORS,
EXECUTE NEXT STATEMENT
```
