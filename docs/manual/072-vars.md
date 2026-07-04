---
name: VARS
order: 72
token: auto
---


PURPOSE:

To list the current variable names and
values that have been assigned.

SYNTAX:
```text

VARS
```

DESCRIPTION:

VARS is short for variables. It is a
useful tool when debugging a program.
Program execution can be halted either
by END, STOP or the BREAK key, and VARS
will display all the current variable
names and their values in the order they
were declared by DIM statements or by
the order they were first referenced in
a program (without a DIM statement). It
is best practice to declare all
variables at the top of a program with
most used variables first, then array
declarations last.

VARS does not list any array variables,
being that there are usually far too
many values assigned in this type of
variable storage. Use an inline FOR/NEXT
loop to print array variables if needed.

NOTE: Using the shift key pauses the
listing allowing the user time to scan
through the list for the desired
variables. Also, you can DUMP the
variables to a printer by using DUMP
VARS.

EXAMPLE:
```text

VARS

MB$="MARK BOWREN"
X= 160
SP$="               "
A= 9693868
N%= 25
NU$=""

READY.
```
