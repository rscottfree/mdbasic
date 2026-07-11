---
name: ON KEY
order: 41
token: auto
---


PURPOSE:

To redirect program execution when data
appears in the keyboard buffer.

SYNTAX:
```text

ON KEY GOSUB line#
[ON] KEY OFF
```

DESCRIPTION:

ON KEY enables the interruption of a
program when a key is pressed, excluding
the Shift, Logo, Ctrl and Restore keys.
This allows a program to focus on other
tasks while still acting on keyboard
input.

line# is the first line number of the
subroutine to GOSUB. If line# is not in
the program, an UNDEF'D STATEMENT ERROR
will occur.

The ASCII value of the key that was
pressed can be accessed using the KEY
variable. When the stop key is disabled
(STOP KEY OFF) the KEY variable will
have the ASCII value 3. See Appendix C
for ASCII characters and values.

While the key trapping subroutine is
executing, key trapping is paused to
avoid multiple calls at the same time.
In this case, the input will go into the
keyboard buffer for the next iteration
of the subroutine.

Use the RETURN statement as you would
with any GOSUB to continue executing
statements from where it was called.
RETURN can also GOTO to a specific line
number instead of going back to where it
was interrupted.

ON KEY OFF or simply KEY OFF will turn
off key trapping.

EXAMPLE:
```text

0 '***ACCEPT KEYS WHILE MAIN LOOP
RUNS***
5 STOPKEYOFF
10 ON KEY GOSUB 1000
.
.(main program loop here)
.
999 PRINT"DONE.":END
1000 CURSOR OFF
1005 IF KEY=13 THEN KEYOFF:RETURN 999
1010 IF KEY=3 THEN KEYOFF:RETURN
1015 PRINT KEY$;:CURSOR ON:RETURN
```
