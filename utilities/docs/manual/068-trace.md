---
name: TRACE
order: 68
token: auto
---


PURPOSE:

To execute a program one line at a time
with display of the current line.

SYNTAX:
```text

TRACE
TRACE [lineNum]
```

DESCRIPTION:

This command is used for debugging
purposes. When a program is being
traced, the line that is being executed
is displayed at the top of the screen.
Pressing the shift key will execute the
first statement on the line. Each press
of the shift key will execute the next
statement on the line before advancing
to the next line. If a control flow
statement (GOTO, GOSUB, RETURN, RESUME)
is encountered then the target line will
be displayed after it executes.

lineNum (optional) is used to start the
program at a specific line number.

TRACE (like RUN) clears all variable
data before executing the program.

Anytime the program goes back into
direct mode the TRACE is disabled so
there is no need to turn it off. This
happens when one of the following
occurs:
1. Program ends
2. STOP statement encountered in program
3. Run/Stop key pressed
4. An error occurs without error
trapping enabled (see ON ERR statement)

NOTE: TRACE will consume the first two
lines on the screen. You may have to
adjust your program to account for this.
Also, if the line listed exceeds 80
characters then the third line fragment
will remain on the screen. It is
preferred to not exceed 80 characters of
BASIC text per line.

EXAMPLE:
```text

TRACE :'RUN PROGRAM AND TRACE THE LINES
TRACE 100 :'START TRACING AT LINE 100
```
