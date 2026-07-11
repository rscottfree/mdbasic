---
name: ELSE
order: 17
token: auto
---


PURPOSE:

To act on a false result of an
expression in an IF statement on the
same line.

SYNTAX:
```text

IF expression THEN (true statements)
:ELSE (false statements)
IF expression THEN line1 ELSE line2
```

DESCRIPTION:

If the expression result is non-zero
(true), all statements between keywords
THEN & ELSE will be executed. If the
expression result is 0 (false), all
statements after the ELSE keyword are
executed. The ELSE keyword is optional
in the IF statement.

The statements THEN and ELSE can be
followed by either a line number for
branching, or one or more statements to
be executed. When THEN is followed by a
line number, a colon before the ELSE
statement is not needed.

Because IF/THEN/ELSE is all one
statement, the ELSE keyword must be on
the same line as the IF keyword. In the
case where the ELSE keyword is
encountered with no corresponding IF
statement, ELSE will behave just like
the REM statement.

Nesting multiple IF statements is legal
but can become confusing. The ELSE
fragment is optional for each IF
statement. Each ELSE statement
corresponds only to the most recent IF
statement. In the following example,
nothing is printed when A is not equal
to B:

IF A=B THEN IF B=C THEN PRINT"A=C" :
ELSE PRINT"A<>C"

By appending another ELSE statement to
the end of the above statement, the case
when A is not equal to B will be
printed:

IF A=B THEN IF B=C THEN PRINT"A=C" :
ELSE PRINT"A<>C" : ELSE PRINT"A<>B"

EXAMPLE:
```text

IF A$="N" THEN PRINT"NO":ELSE PRINT"YES"
:'YES OR NO WILL BE PRINTED
IF X THEN 100 ELSE 200 :'GOTO 100 IF
X<>0, 200 IF X=0
IF X=1 THEN 200 ELSE X = 0 :'GOTO 200 IF
X=1, OTHERWISE LET X=0
```
