---
name: LINE INPUT
order: 32
token: auto
---


PURPOSE:

To input a string of characters from the
keyboard that is terminated by a
carriage return.

SYNTAX:
```text

LINE INPUT ["prompt",] A$ [,B$ [,C$ [,…
] ]]
```

DESCRIPTION:

LINE INPUT is much like the INPUT
statement, except LINE INPUT accepts
input of any character (except return
key). This is useful for inputting
strings that may contain commas or
semicolons, or when no prompt is needed.

"prompt" (optional) is a literal string
of characters that will be displayed as
a message to the user. This string
cannot be a variable.

A$ is the variable that will store the
string of characters from the current
input device which typically is the
keyboard. It is legal to supply multiple
strings (B$, C$,…,Z$) each separated by
a comma to capture multiple lines of
input consecutively.

The return key is the only delimiter for
the end of the input string. The input
from the keyboard it is limited to 80
characters.

Any attempt to use INPUT or LINE INPUT
in direct mode will cause the ILLEGAL
DIRECT ERROR due to the fact that the
same buffer that captures the input line
of text is used to process (tokenize)
the command line input.

Use the LINE INPUT# statement to input a
line of characters from an open file.

EXAMPLE:
```text
LINE INPUT A$ :'NO PROMPT, INPUT ONE
STRING
LINE INPUT A$, B$ :'NO PROMPT, INPUT 2
STRINGS
LINE INPUT"->", A$, B$ :'PROMPT ONCE,
THEN INPUT 2 STRINGS
```
