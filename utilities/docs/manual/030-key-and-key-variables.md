---
name: KEY and KEY$ (variables)
order: 30
token: auto
---


PURPOSE:

To return the ASCII value of the last
key pressed when key trapping is
enabled.

SYNTAX:
```text

K = KEY
K$ = KEY$
KEY = ascii
```

DESCRIPTION:

These variables are used in conjunction
with the ON KEY GOSUB statement to
return the ASCII value of the key that
was pressed. The value will be retained
until the next keystroke is trapped.
When combining a key with the Ctrl,
Shift or Logo keys, the ASCII value is
changed accordingly. During subroutine
execution, key trapping is paused until
a RETURN statement is executed. It is
turned off entirely any time the KEY OFF
statement is executed.

The KEY variable can be manually changed
to any ASCII value (0 to 255). This is
useful when filtering keys during
evaluation of the ASCII. Changing the
value of KEY immediately changes KEY$
which cannot be changed directly. See
example below.

EXAMPLE:
```text

0 '***ON KEY GOSUB EXAMPLE***
1 'GET KEY STROKES WHILE MAIN LOOP RUNS
2 'PRG ENDS WHEN ENTER KEY PRESSED
10 CURSOR ON
20 PRINT">";
30 ON KEY GOSUB 100
40 '**YOUR MAIN PROGRAM LOOP STARTS
HERE**
50 WAIT1:WAIT1:WAIT1:WAIT1:WAIT1
:'SIMULATE RUNNING PRG
60 GOTO 40
70 '**NO KEY TRAP SECTION OF PRG GOES
HERE**
80 CURSOR OFF
85 PRINT:PRINT"DONE."
90 END
100 CURSOR OFF
105 KEY = (KEY AND 127) : IF KEY = 13
THEN KEY OFF : RETURN 70
110 IF KEY<32 THEN KEY=0
115 PRINT KEY$; : CURSOR ON : RETURN
```
