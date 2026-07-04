---
name: SAVE
order: 57
token: auto
---


PURPOSE:

To write content of RAM to a device for
later retrieval with LOAD.

SYNTAX:
```text

SAVE
SAVE [filename$] [,device] [,secondary]
SAVE address1, address2 [,filename$]
[,device] [,secondary]
```

DESCRIPTION:

SAVE is a CBM BASIC command that has
been augmented to support saving a
contiguous section of RAM. This type of
save is commonly referred to as a
"binary save". The first syntax listed
above is the CBM BASIC syntax which is
from the start address of BASIC program
text ($0800) to the address of the end
of the current BASIC program text. The
second syntax is the augmented SAVE
which supports a custom address range.

Some examples that make use of a binary
SAVE are:
1. Save sprite data to a file for quick
retrieval with LOAD
2. Save a BASIC program with an appended
assembly language subroutine.
3. Save the video matrix (text screen)

NOTE: To save the screen with color, the
bitmap or a redefined character set use
the associated secondary address as
described in Appendix A.

address1 (0-65535) is the start address
in RAM for the first byte to save.

address2 (0-65535) is the end address in
RAM for the last byte to save.

filename$ is the name of the file and
should not exceed 16 characters. Tape
devices do not require a name for the
file and can be an empty string.

device (0-11, default 1) is the device
number to write the bytes.
0=Keyboard, 1=Dataset, 2=RS-232/User
Port, 3=Screen, 4-5=Printer, 8-11=Disk

secondary (0-31 for serial devices,
0-127 for other devices, default 0) is
the secondary address value with meaning
that is specific to the device.

EXAMPLE:
```text

SAVE "MY_BAS_PRG", 8 :'SAVE CURRENT
BASIC PROGRAM TO DISK
SAVE $C000, $CFFF, "ML_PRG", 8 :'SAVE 4K
BYTES IN HIRAM TO DISK
SAVE 1024, 2023, "SCREEN", 8 :'SAVE TEXT
SCREEN TO DISK
```
