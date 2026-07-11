---
name: CLOSE
order: 8
token: auto
---


PURPOSE:

To close logical files that have been
opened.

SYNTAX:
```text

CLOSE filenum1 [,filenum2 [,filenum3
...]]
CLOSE FILES
```

DESCRIPTION:

CLOSE is the CBM BASIC statement used to
close logical files by number. It has
been augmented to enable closing
multiple files or all open files. If the
file number being closed is the current
CMD I/O channel then it is reset to use
the default I/O devices (keyboard and
screen). This handles the quirk
experienced in CBM BASIC that left the
I/O directed at a closed channel.

filenum (1-255) is the logical file
number to close. You can close multiple
files by separating them with a comma.
No error will occur if the file is not
open. The files are closed in the order
they appear in the parameter list. CBM
BASIC file numbers 128-255 are intended
for line printers so a linefeed
character is appended after every
carriage return from a PRINT# statement.
File number 0 is invalid and ignored
without error.

CLOSE FILES will close all logical files
and restore default I/O devices (screen
and keyboard). If there were no open
files to close then only the default I/O
devices are restored.

If the file number being closed was
opened using device 2 (RS-232 port) then
the I/O buffer memory is released back
to BASIC and all variable values are
lost. To avoid this problem use the
SERIAL statement for RS-232
communications.

CBM BASIC is limited to a maximum of 10
open files. Any attempt to exceed this
value will result in TOO MANY FILES
ERROR. You can check the current number
of open files using the INF function
with parameter value 8.

EXAMPLE:
```text

CLOSE 1       :'CLOSE FILE 1
CLOSE 1,7,9   :'CLOSE FILES 1,7 AND 9
CLOSE FILES   :'CLOSE ALL FILES
IF INF(8) > 0 THEN CLOSE FILES :'CLOSE
ALL FILES ONLY IF ANY ARE OPEN
```
