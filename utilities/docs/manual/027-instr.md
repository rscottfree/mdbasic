---
name: INSTR()
order: 27
token: auto
---


PURPOSE:

To find the index of the first
occurrence of a string that is inside
another string.

SYNTAX:
```text

I = INSTR([index,] source$, find$)
```

DESCRIPTION:

INSTR is a function that returns the
ordinal index number of the first
occurrence of a string within another
string. The index of a string always
starts at 1 unless specified. The return
value of 0 indicates the string was not
found.

INSTR will always return 0 in the
following cases:
1. The length of find$ is 0 (null or
empty string)
2. The length of find$ is greater than
the length of source$
3. The find$ was not found in source$

index (1-255, default 1) is an optional
numeric expression to specify the
ordinal of where in the string to start
the search. When omitted the index is
1.

source$ is the string to search.

find$ is the string being sought.

NOTE: Using INSTR in immediate mode with
both source$ and find$ string parameters
as literal string values will produce
incorrect results when the find string
is found toward the end of the source
string. This is due to the fact that
both strings are temporary strings
(copied from the command line) which
causes the find string to overlap the
end of the source string during
evaluation. This can be avoided by using
a variable for at least one of the
string parameters. This will not happen
in program mode since the literal string
values in the program text are used
during evaluation.

EXAMPLE:
```text

10 S$="MDBASIC IS COOL":F$="IS"
20 I%=INSTR(S$, F$)
30 IF I%=0 THEN PRINT"NOT FOUND!":ELSE
PRINT MID$(S$, I%, LEN(F$))
```
