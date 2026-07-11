---
name: WAIT
order: 75
token: auto
---


PURPOSE:

To perform a timed pause in program
execution or wait for a value in a
specified memory location.

SYNTAX:
```text

WAIT location, mask1 [,mask2]
WAIT jiffies
```

DESCRIPTION:

WAIT is a CBM BASIC statement that has
been augmented to also perform a timed
pause in program execution which can be
aborted by pressing the run-stop key.
The original CBM BASIC WAIT statement
causes program execution to suspend
until a given memory address matches a
specified bit pattern and can only be
aborted by pressing the run-stop &
restore key combination.

location (0-65535) is the memory address
to compare the mask values.

mask1 (0-255) is the value to be ANDed
with the memory location’s value.

mask2 (0-255) is an optional value to
exclusive-OR with the result of mask1.

mask1 "filters-out" any bits that you
don't want to test. Where the bit is 0
in mask1, the corresponding bit in the
result will always be 0. The mask2 value
flips any bits, so that you can test for
an off condition as well as an on
condition . Any bits being tested for a
0 should have a 1 in the corresponding
position in mask2.

jiffies (0-65535) is an unsigned integer
of the number jiffies (approximately one
sixtieth of a second) to wait. Any value
outside this range will result in an
ILLEGAL QUANTITY ERROR.

There are many reasons for using a timed
delay including waiting for the user to
read the screen, a musical note to
complete or slow down program execution.

EXAMPLE:
```text

WAIT 300 :'WAIT FOR 5 SECONDS (300
JIFFIES)
WAIT $DD01,$80 :'WAIT TILL $DD01 IS
EXACTLY $80
WAIT $DD01,$80,$7F :'WAIT TILL BIT 7 IS
SET IN MEM $DD01
```
