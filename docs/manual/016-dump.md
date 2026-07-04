---
name: DUMP
order: 16
token: auto
---


PURPOSE:

To send output to the printer connected
on device 4.

SYNTAX:
```text

DUMP LIST [start]-[stop]
DUMP SCREEN [size]
DUMP VARS
DUMP FILES [volume$]
DUMP [expression]
```

DESCRIPTION:

This command is very useful when a
hard-copy is needed for a program
listing, text or bitmap screen. There
are two printer device numbers (4 and 5)
but DUMP can only send output to device
4.

DUMP LIST start-stop works just like the
list routine, except the listing goes on
the printer.

DUMP FILES [volume$] will print the
directory of the disk on the printer.

DUMP SCREEN will print current text
screen to the printer. If the currently
display screen is a bitmap (SCREEN 5)
then the bitmap is printed. The
additional parameter size (1 = 1x size,
2 = 2x size, default = 1) is available
for the bitmap screen only.

DUMP expression represents any variable,
string or numeric, to be printed on the
printer. When not using the other three
configurations, DUMP works just like the
PRINT command, except the output is only
to the printer.

DUMP VARS lists the currently
dimensioned variables to the printer.

EXAMPLE:
```text

DUMP LIST 100- :'DUMPS PROGRAM LISTING
FROM LINE 100
DUMP SPC(3)+"PRINTER OK." :'SIMPLE TEST
FOR PRINTER
SCREEN 0:DUMP SCREEN :'DUMPS EVERYTHING
ON TEXT SCREEN 0
SCREEN 5:DUMP SCREEN 2 :'PRINT BITMAP
SCREEN ENLARGED 2X
```
