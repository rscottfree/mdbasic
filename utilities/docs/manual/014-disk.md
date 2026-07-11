---
name: DISK
order: 14
token: auto
---


PURPOSE:

To send DOS commands to the disk
drive(s).

SYNTAX:
```text

DISK command$ [,device [,result$]]
```

DESCRIPTION:

The DISK statement is used to send DOS
(Disk Operating System) commands to a
selected disk drive, eliminating the
need for opening, printing & closing the
command channel. All commands offered by
the DOS version in the disk drive are
available. When executed in immediate
mode the status of the command is
displayed. In program mode the message
is suppressed, however, it can be
captured into a string variable.

command$ is a string of characters
containing the drive number, function to
perform, and the parameters to sent to
the drive. An empty string will just
report the drive status. The following
are the commands offered by the 1541
DOS:

<!-- table: mode=sections -->
| COMMAND | SYNTAX (d=drive number) | DESCRIPTION |
|--|--|--|
| NEW | "Nd:disk name,id" | Full format with ID & label |
| NEW | "Nd:disk name" | Soft format (BAM only) with label |
| COPY | "Cd:new file=d:original file" | Copy a file |
| RENAME | "Rd:new name=old name" | Rename a file |
| SCRATCH | "Sd:file name" | Delete a file |
| INITIALIZE | "Id" | Initialize a disk (clear errors) |
| VALIDATE | "Vd" | Validate a disk (find problems) |

device (8-11, default 8) is the optional
device number of the disk drive.

result$ is an optional string variable
to store the DOS response message. The
response is in the format
"Status,Message,Info1,Info2". Below are
some examples.

00, OK,00,00
00,FILES SCRATCHED,01,00

EXAMPLE:
```text

DISK"I0" :'INITIALIZE DRIVE 0
DISK"N0:JUNK DISK,JD" :'FORMAT DRIVE 0,
NAME="JUNK DISK", ID="JD"
DISK"V" :'VALIDATES DISKETTE IN DRIVE 0
DISK"S1:POKER" :'ERASES PROGRAM "POKER"
ON DRIVE 1
DISK"C1:DATA=0:DATA" :'COPIES "DATA"
FROM DRIVE 0 TO DRIVE 1
```
