---
name: POKE
order: 47
token: auto
---


PURPOSE:

To write a value to one or more RAM
memory locations or to copy bytes from
one location to another.

SYNTAX:
```text

POKE address1, value
POKE address1 TO address2, value
[,operation [,step]]
```

DESCRIPTION:
POKE is the CBM BASIC statement to write
a value to memory. MDBASIC has augmented
this statement to write a value to
multiple sequential addresses. This is
many times faster than using a FOR/NEXT
loop.

address1 (0-65535) is the start address
to perform operation.

address2 (0-65535) is the end address to
perform operation.

value is an unsigned integer on which to
perform an operation. Operations 0-4
have a range of 0-255. Operation 5
(copy) has a range from 1-32727 which is
the number of bytes to copy from
address1 to address2 with a given
address step.

operation (0=none/set, 1=AND, 2=OR,
3=EOR, 4=RASTERAND, 5=COPY, default 0)
is the process to perform on the value
when applying the result to the
specified addresses. When omitted, the
default operation is 0 which simply
writes the value to memory. Operation 4
(RASTERAND) performs an AND operation on
the value with the current screen raster
scan line. Operation 5 copies the bytes
from address1 (source) to address2
(destination) with the number of bytes
to copy specified by the value
parameter.

step (1-255, default 1) is the address
increment to use when calculating the
next address in the specified range.

Using POKE by address range can be used
to quickly change sprite images, screen
text or color with a specific pattern.
It can also be used to totally clear the
current BASIC program and data when a
program exits. This type of POKE can
easily corrupt the system memory so use
with caution.

EXAMPLE:
```text

POKE 1024,1 :'WRITE THE VALUE 1 TO MEM
ADDRESS 1024
POKE 13*64 TO 13*64+63,255,3 :'NEGATE
SPRITE IMAGE OF DATA INDEX 13
POKE $0800 TO $7FFF,0 :'CLEAR BASIC PRG
AND ALL VARIABLE DATA
POKE $0400 TO $07E7, %10000000, 3 :'FLIP
BIT 7 OF ALL CHARS ON SCREEN
POKE $0400 TO $C000, 1000, 5 :'COPY TEXT
PAGE 0 TO PAGE 1 (1000 BYTES)
```
