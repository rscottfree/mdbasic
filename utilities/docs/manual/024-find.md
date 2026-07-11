---
name: FIND
order: 24
token: auto
---


PURPOSE:

To search a BASIC program for keywords
or a sequence of characters.

SYNTAX:
```text

FIND"string
FINDcode
```

DESCRIPTION:

FIND is used for searching program text
(in memory) for a specific keyword or
string sequence. Large programs can be
difficult to manually find things like
what strings have been used, statements
that have been used, or a miscellaneous
string of characters. FIND is a fast,
useful debugging tool for programmers.

"string is used when searching for ASCII
text (not keywords). The ending
quotation mark is left off unless it is
part of the string being sought.

code is used when searching for
statement keywords. The exact syntax
(including any spaces & quotations) will
be included in the search.

When FIND makes a match, the line is
displayed and the search process
continues until the end of the program
is reached. If the BREAK key is pressed
during a search, the process stops
immediately and displays the BREAK IN
(line) message indicating where the
search was when it was interrupted.

NOTE: All statements following the FIND
statement will be included in the
search. Every character or statement
will be searched, including REM, colons,
quotations, spaces etc.

EXAMPLE:
```text

Find all occurrences of string
assignment (no spaces)
FINDA$=

Find all occurrences of keyword GOSUB
with space then digits 200
FINDGOSUB 200

Find all occurrences of exact string
FIND"METEOR
```
