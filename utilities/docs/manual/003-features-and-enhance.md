---
name: FEATURES & ENHANCE.
order: 3
token: none
---

MDBASIC adds enhanced file loading and
saving features described briefly here.
See Appendix A for more details.

Device Numbers for loading & saving
special data:
16 Text screen & colors including
background & border
17 Character designs (see DESIGN
command)
18 Bitmaps complete with colors &
resolution mode (see SCREEN command)

SAVE "MYSCREEN",8,16 :'SAVE CURRENT
SCREEN’S TEXT & COLORS TO FILE

LOAD "MYBITMAP",8,18 :'LOAD & SHOW
BITMAP FROM FILE

You can also save a specific chunk of
RAM (binary save):

SAVE $0400,$07F8,"MYSCREEN",8 :'SAVE
ONLY THE VIDEO MATRIX TO FILE

When loading files, the start & end
address will be displayed after loading
is complete. For example:

LOAD"MYPRG",8,1

SEARCHING FOR MYPRG
LOADING 49152-50059
READY.

In addition, MDBASIC will load binary
files (pictures, machine code, etc.)
without corrupting BASIC’s memory
pointers. A LOAD statement can be in a
BASIC program to load binary files
anywhere in memory (except $8000-$BFFF
which is reserved for MDBASIC) without
losing variable data or causing an OUT
OF MEMORY error. The programmer must
ensure that the target memory locations
are available. For example, you would
not want to load a file on top of where
your program or variables are stored.
Instead, manually adjust the BASIC
memory pointers with a few POKE
statements before loading. The safest
approach is to load binaries into upper
memory ($C000-$CFFF). Bitmap graphics
can be directly loaded into $E000-$FFFF
(RAM under Kernal ROM) then shown by
using the SCREEN statement.

MDBASIC supports numeric constants of
base 2 (binary), 8 (octal) or
hexadecimal and new functions have been
added to convert the string
representation. The NOT expression
short-hand is the exclamation point. REM
(remark) short-hand is the apostrophe.
See examples below:

B = %00001111 :'BINARY 15
H1 = $FFFF :'HEX CONSTANT 65535
H2 = VALH("C000") :'HEX STRING 49152
H$ = HEX$(65535) :'DECIMAL 65535 TO HEX
STRING FFFF
O = @20 :'OCTAL CONSTANT 16
X = !X :'SAME AS X = NOT X

The LIST command has been enhanced with
the ability to freeze the listing
process by holding down the Shift key.
Editor modes Quote, Insert and Reverse
can be easily aborted by simply pressing
the Restore key.
