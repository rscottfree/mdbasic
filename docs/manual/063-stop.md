---
name: STOP
order: 63
token: auto
---


PURPOSE:

To pause a running BASIC program or
enable/disable the STOP statement or
key.

SYNTAX:
```text

STOP
STOP ON | OFF
STOP KEY ON | OFF
```

DESCRIPTION:

The STOP statement is a CBM BASIC
statement that was augmented to provide
additional features. Normally the STOP
statement is used to pause a running
BASIC program for debugging purposes.
The BREAK ERROR IN line# message is
displayed and the programmer can
interrogate system state (see VARS
command).

STOP ON | OFF (default ON) allows the
programmer to enable or disable the STOP
statement. This is handy when the
program is to run normally without
interruption but leaving the various
STOP statements in the code for future
debugging. This statement would
typically be at the top of a program
that uses this debugging feature.

STOP KEY ON | OFF (default ON) allows
the programmer to decided if the Stop
key is allowed to stop the program. This
allows the ability to capture the key
press in a BASIC program and act on it
accordingly. For example you may want to
prompt the user to confirm they would
like to exit the program and if so, do
some final housekeeping activities to
shut down gracefully.

When the Stop key is disabled the ASCII
value 3 will be returned when reading
from the keyboard. The Stop key and STOP
statements are enabled when starting a
program using the RUN command but will
remain unchanged when using RUN@ with a
file. Refer to the KEY and RUN
statements for more information.

EXAMPLE:
```text

10 STOP KEY OFF
20 KEY GET A:IF A=0 THEN20
30 IF A=3 THEN 50
40 PRINT A:GOTO 20
50 PRINT"QUIT NOW (Y/N)? ";
60 CURSOR ON:KEY WAIT A$:CURSOR OFF
70 IF A$="Y" THEN PRINTA$:STOP KEY
ON:END
80 IF A$="N" THEN PRINTA$:GOTO 20 ELSE
60
```
