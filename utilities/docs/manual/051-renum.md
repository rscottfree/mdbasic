---
name: RENUM
order: 51
token: auto
---


PURPOSE:

To renumber a BASIC program with a
specific line increment.

SYNTAX:
```text

RENUM
RENUM [start] [,increment]
```

DESCRIPTION:

The RENUM command is used to renumber
all BASIC program lines while
maintaining line number references in
statements like GOTO, GOSUB, etc.
Renumbering is typically done to add
numerical separation between each
program line to make it easy to insert
additional lines. Consistent line
numbering also makes a program look neat
and easy to follow. When merging two
programs together using MERGE command,
both programs should be renumbered so
that the line numbers do not overlap.
Refer to the MERGE command for more
details.

start is the optional (default 0) new
starting line number for the program.

increment is the optional (default 10)
number of lines between every line.

If RENUM has no operands, then the
default value of 10 will be used for the
start line number and increment.

RENUM changes all line numbers after
keywords that may be followed by one or
many comma-separated line numbers. These
keywords are:

THEN, ELSE, GOTO, GOSUB, RESTORE,
RETURN, RESUME, RUN, ERRL=

If RENUM encounters a reference to a
line number that is not in the program,
the number is replaced with 65535. On
completion the list of any such lines
having this problem is displayed and
should be corrected immediately.

RENUM will display a period for every
line completed. The entire process can
take several seconds depending on the
size of the program and the number of
statements that reference line numbers.
Expect to wait an average of 5 seconds
per 100 lines of code.

EXAMPLE:
```text

RENUM :'PROGRAM STARTS WITH LINE 10 WITH
10 INCREMENTS
RENUM 1000,10 :'PROGRAM STARTS WITH LINE
1000 WITH 10 INCREMENTS
RENUM 100 :'PROGRAM STARTS WITH LINE 100
WITH 100 INCREMENTS
```
