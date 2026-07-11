---
name: FILES
order: 21
token: auto
---


PURPOSE:

To display the directory of the current
diskette.

SYNTAX:
```text

FILES
FILES [volume$] [,device]
```

DESCRIPTION:

FILES allows the listing of the
directory without loading it into
memory. The directory is displayed in
the normal CBM DOS directory format with
the addition of the total number of
files.

FILES, with no parameters, will list the
entire directory from drive 0, device
8.

volume$ ("d:volume") is the search
string to filter file names that equal
or start with a specific character
sequence using the asterisk symbol at
the end of the string. The volume$
parameter can optionally contain the
drive number d: (0 or 1, default=0) for
when two drives are chained together on
the same device number. The maximum
length of a file name is 16 characters,
therefore the maximum length of the
volume$ parameter should never exceed 18
characters.

device (8-11, default 8) is the optional
device number of the disk drive.

The listing of the directory can be
paused by pressing the shift key, and
aborted by pressing the control or break
keys. The running file count will be
displayed.

EXAMPLE:
```text

FILES :'ALL FILES ON DRIVE 0, DEVICE 8
FILES,9 :'ALL FILES ON DRIVE 0, DEVICE 9
FILES"1:*",9 :'ALL FILES ON DRIVE 1,
DEVICE 9
FILES"A*" :'ALL FILES ON DRIVE 0 THAT
START WITH A
FILES"0:A*"             :'SAME AS ABOVE
FILES"1:*" :'ALL FILES ON DRIVE 1,
DEVICE 8
FILES"0:*",10 :'ALL FILES ON DRIVE 0,
DEVICE 10
```
