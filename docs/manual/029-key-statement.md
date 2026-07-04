---
name: KEY (statement)
order: 29
token: auto
---


PURPOSE:

To assign one of the 8 function keys,
display the current function key
assignments, put characters in the
keyboard buffer, clear the buffer and
wait for any single key input.

SYNTAX:
```text

KEY keynum, assign$
KEY string$
KEY LIST | OFF | CLR
KEY GET variable
KEY WAIT [variable]
```

DESCRIPTION:

The KEY statement has various forms and
uses in both direct and immediate mode.
Function key assignments work only in
immediate mode.

keynum (1-8) selects which function key
to assign text.

assign$ is the string of characters
(maximum 16) that will be assigned to
the function key. Adding +CHR$(13) at
the end of this string will act as if
the user pressed the return key and
cause the command to be executed.

string$ (0 to 255 characters) is a
string of characters to put into the
keyboard buffer as if the user entered
them.

KEY LIST displays the current key
assignments in immediate mode.

KEY OFF turns off key trapping. See the
ON KEY statement for more info.

KEY CLR clears the keyboard buffer.

KEY GET variable fetches a key from the
keyboard buffer. If the buffer is empty
then the variable will be zero or an
empty string depending on the type.

KEY WAIT waits for a key to appear in
the keyboard buffer with an optional
variable for storing the ASCII value.
When no variable is provided the key
will remain in the buffer and the
program will continue to the next
statement.

EXAMPLE:
```text

KEY 1,CHR$(147)+"LIST"+CHR$(13) :'ASSIGN
FUNCTION KEY 1 TO LIST PROGRAM
KEY "N":INPUT A$ :'INPUT WITH DEFAULT
USER RESPONSE
KEY WAIT K: PRINT K, CHR$(K) :'WAIT FOR
A KEY, PRINT ASCII AND CHR
```
