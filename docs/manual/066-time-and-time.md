---
name: TIME and TIME$
order: 66
token: auto
---


PURPOSE:

To get or set the Time of Day (TOD).

SYNTAX:
```text

TIME CLR
T = TIME
T$ = TIME$
TIME$ = tod$
```

DESCRIPTION:

TIME returns the number of seconds since
midnight. TIME$ returns the string
representation of the clock (TOD #2) in
24-hour format (military time). It also
is used to set the clock to a specified
time. When the computer is switched on
the time starts at 01:00:00 (1 AM). When
the clock reaches midnight it rolls over
to 12 AM (00:00:00). This clock is based
on a hardware real time clock which
continues keep time even after a soft
reset of the computer. It is not driven
or affected by software interrupts and
thus keeps time more accurately than the
CBM BASIC’s jiffy clock referenced by
variables TI and TI$.

TIME CLR can be used to set the clock to
midnight 00:00:00 (12 AM).

T is a floating point variable to
capture the current number of seconds
since midnight from the TOD clock. It is
accurate to 1/10th of a second. The
minimum value possibly returned by TIME
is 0.0 and the maximum is 86399.9.

T$ is a string variable to capture the
current time string from the TOD clock.

tod$ is an 8 character string in the
format "hh:mm:ss" used to set the TOD
clock. The time is represented as a
24-hour clock (00:00:00 to 23:59:59). hh
is the hours (00-23), mm is the minutes
(00-59) and ss is the seconds (00-59).
If the string supplied is not in the
exact format a TYPE MISMATCH ERROR will
occur. The clock immediately advances
forward from the time that was set.

EXAMPLE:
```text

T = TIME :'GET THE NUMBER OF SECONDS
SINCE MIDNIGHT
PRINT TIME$ :'PRINT THE CURRENT TIME IN
STRING FORMAT
TIME$ = "13:00:00" :'SET THE TIME TO 1
O’CLOCK PM
TIME CLR :'SET THE TIME TO MIDNIGHT
"00:00:00"
H = VAL(MID$(TIME$,1,2)) :'GET HOURS
FROM TIME
M = VAL(MID$(TIME$,4,2)) :'GET MINUTES
FROM TIME
S = VAL(MID$(TIME$,7,2)) :'GET SECONDS
FROM TIME
```
