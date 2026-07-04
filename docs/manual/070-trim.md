---
name: TRIM$()
order: 70
token: auto
---


PURPOSE:

To return a new string copied from
another string with all leading and
trailing spaces removed.

SYNTAX:
```text
F$ = TRIM$(S$)
```

DESCRIPTION:

TRIM$ returns a new string copied from
the source string S$ with all leading
and trailing spaces removed. If the
source string contains only spaces then
the result is an empty string.

This functionality is commonly referred
to as trimming the string, thus many
other programming languages use the
keyword TRIM. It is especially useful
when dealing with sloppy user input or
parsing text files.

The CBM BASIC statements to perform this
function is a bit ugly and would not
perform as well because it involves
searching both sides of the string for
the first non-space character and then
returning the MID$ result.

When assigning the result to a string
variable be aware that a new string is
being created on each use. This also
happens when simply assigning one string
to the value of another. Heavy use of
string assignments can trigger a garbage
collection. If it cannot be avoided,
like inside a loop reading the contents
of a file, be sure to trigger a garbage
collection manually. This can be done by
using the statement SYS46374 or the
function FRE(0). This approach will
ensure that a large amount of discarded
strings will not pile up thus avoiding a
long- running garbage collection
process.

EXAMPLE:
```text

0 '*TEST TRIM OF LEAD & TRAIL SPACES*
10 S$=" THIS IS A TRIM$ TEST "
15 PRINT"SOURCE STRING:"
20 PRINT CHR$(34);S$;CHR$(34)
25 PRINT"LENGTH:";LEN(S$)
30 F$=TRIM$(S$)
35 PRINT:PRINT"RESULT STRING:"
40 PRINT CHR$(34);F$;CHR$(34)
45 PRINT"LENGTH:";LEN(F$)
```
