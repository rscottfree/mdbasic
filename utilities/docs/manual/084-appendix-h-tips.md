---
name: APPENDIX H: TIPS
order: 84
token: none
---

PROGRAMMING GUIDELINES AND SUGGESTIONS:

1. Declare all non-array variables at
the top of the program with the most
used variables first. This is because
the name lookup is a sequential process
starting from the first declared
variable to the last.

2. Always place array declarations at
the end of the declare section. This
will avoid moving array data in memory
since array data is stored after
non-array.

3 Declare constants in a variable if
they are heavily used or inside a loop.
It is faster to access a variable value
than to decode 5 or more ASCII digits.

4. Integer arrays use less space than
non-array integers. If you have many
integer variables or constants, consider
using an array to reference the value
instead of individual integer variables.

5. Any subroutine that repeatedly
perform string concatenation or
reassignment should manually execute a
garbage collection by using SYS46374 or
the FRE(0) function. This will help
avoid an automatic collection which can
take a significant amount of processing
time during which the BASIC program is
paused.

6. MDBASIC makes use of a few memory
locations that are not used by CBM BASIC
or the Kernal. Do not use these
locations to store any info or sprite
data as it will be lost. These include
zero-page locations $FB to $FE. Location
$0313 is used as bit flags to control
which MDBASIC IRQ subroutines are
active. Locations $0334 & $0335 are used
to store the previous IRQ vector while
MDBASIC IRQ driven processes are
running. Locations $0336 to $033B
temporarily hold vectors to BASIC
program text for the normal error
handler, custom error handler and key
trapping.

USEFUL PEEKS AND POKES
Although MDBASIC was written to help
reduce the use of the PEEK and POKE
statements, sometimes it is necessary to
still use them. The INF function returns
most system information to avoid the use
of PEEK. All other statements and
functions help avoid the use of the POKE
statement. Below are useful PEEKs and
POKEs for which MDBASIC does not provide
a statement or function.

POKE 808,234 :'DISABLE STOP/RESTORE KEY
COMBO (BREAKS LIST COMMAND)

POKE 650,128 :'KEYS REPEAT 0=CURSOR,
INSERT, DELETE & SPACE, 64=NONE, 128=ALL

POKE 657, 128 :'SHIFT/LOGO CHARSET
SWITCH: 0=ENABLE, 128=DISABLE
'ALTERNATIVELY, PRINT CHR$(9) TO ENABLE,
CHR$(8) TO DISABLE

C1 = PEEK(53278) :'SPRITE TO SPRITE
COLLISION (8-BITS)
C2 = PEEK(53279) :'SPRITE TO TEXT
COLLISION (8 BITS)
