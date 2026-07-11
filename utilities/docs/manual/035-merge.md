---
name: MERGE
order: 35
token: auto
---


PURPOSE:

To merge a program from disk or tape to
the end of a program in memory.

SYNTAX:
```text

MERGE filename$ [,deviceNum]
```

DESCRIPTION:

MERGE allows the combining of programs
to constitute one program in memory. The
process merges the two programs into RAM
memory only. If a new file is to be
created, the final product must be saved
to a new file.

Before two programs are merged, the
first program must be in RAM memory,
which will be the beginning of the
program. The second program must be on
tape or disk.

Be sure to renumber both programs
separately so that when they merge
together the line numbers do not
overlap. The merging program’s start
line number should be higher than the
last line number of the program in
memory. Refer to the RENUM command for
more information.

filename$ is the file name of the
program that is to be connected to the
end of the program in RAM memory. For
tape devices the string can be empty.

deviceNum (0-31, default 1) is the
device number from where the merging
program will load. Device 1 is for tape,
devices 8 to 12 are for disks.

When MERGE is executed with no
parameters the default behavior of LOAD
is used which is to MERGE the first file
found on the tape device.

NOTE: No secondary address is specified
because MERGE is only for BASIC
programs.

EXAMPLE:
```text

MERGE"SUBROUTINE",8
```
