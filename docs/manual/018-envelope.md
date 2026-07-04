---
name: ENVELOPE
order: 18
token: auto
---


PURPOSE:

To set the duration of the volume
envelope phases (attack, decay, sustain,
release) for a given voice.

SYNTAX:
```text

ENVELOPE voice, attack, decay [,sustain,
release]
```

DESCRIPTION:

When a note is played on a musical
instrument, the volume does not suddenly
rise to a peak and then cut off to zero.
Rather, the volume builds to a peak,
levels off to an intermediate value, and
then fades away. This creates what is
known as a volume envelope.

The SID chip allows the volume envelope
of each voice to be controlled so that
specific instruments may be imitated or
new sounds created. This is done via the
attack/decay and sustain/release
settings. The cycle is started by using
the WAVE statement.

The first phase of the envelope, in
which the volume builds to a peak, is
known as the attack phase. The second,
in which it declines to an intermediate
level, is called the decay phase. The
third, in which the intermediate level
of volume is held, is known as the
sustain period. The final interval, in
which the sound fades away, is called
the release cycle.

voice (1-3) selects which voice to apply
the settings.

attack (0-15) is time over which the
volume of the tone will rise from 0 to
its peak. The 16 durations to choose
from set the elapsed time of this cycle
as follows:

| VALUE | DURATION |
|--|--|
| 0 | 0.002 seconds |
| 1 | 0.008 seconds |
| 2 | 0.016 seconds |
| 3 | 0.024 seconds |
| 4 | 0.038 seconds |
| 5 | 0.056 seconds |
| 6 | 0.068 seconds |
| 7 | 0.080 seconds |
| 8 | 0.100 seconds |
| 9 | 0.250 seconds |
| 10 | 0.500 seconds |
| 11 | 0.080 seconds |
| 12 | 1.000 seconds |
| 13 | 3.000 seconds |
| 14 | 5.000 seconds |
| 15 | 8.000 seconds |

decay is the time over which the volume
of the tone declines from the peak
reached in the attack phase to the
sustain level. The 16 durations to
choose from set the elapsed time of this
cycle as follows:

| VALUE | DURATION |
|--|--|
| 0 | 0.006 seconds |
| 1 | 0.024 seconds |
| 2 | 0.048 seconds |
| 3 | 0.972 seconds |
| 4 | 0.114 seconds |
| 5 | 0.168 seconds |
| 6 | 0.204 seconds |
| 7 | 0.240 seconds |
| 8 | 0.300 seconds |
| 9 | 0.750 seconds |
| 10 | 1.500 seconds |
| 11 | 2.400 seconds |
| 12 | 3.000 seconds |
| 13 | 9.000 seconds |
| 14 | 15.000 seconds |
| 15 | 24.000 seconds |

NOTE: The values in the chart above
apply to both decay and release cycles.

sustain (0-15) selects the volume level
at which the note is sustained following
the decay cycle. The volume of the the
voice will remain at the selected
sustain level until the release cycle is
started using the WAVE statement.

release (0-15) is the duration of time
in which the volume fades from the
sustain level to near zero volume. The
duration of the release cycle
corresponds to the values in the decay
chart. The cycle is started by using the
WAVE statement.

The attack, decay, sustain cycle is
started by the WAVE statement by setting
the gate operand to 1. The sound being
emitted will stay at the sustain volume
until the release cycle is started by
setting the gate operand to 0.

You may notice the volume of the sound
does not quite reach 0 at the end of the
release cycle. There are three options
to completely turn off the sound to get
rid of the residual noise:
1. Set the master volume to zero (VOL
statement)
2. Disable the voice's oscillator output
(WAVE statement)
3. Route the voice to the no-pass filter
(FILTER statement)

EXAMPLE:
```text

ENVELOPE 1,1,5 :'VOICE 1 CHANGE
ATTACK/DECAY ONLY
ENVELOPE 1,15,15,15,15 :'VOICE 1 MAX
VALUES FOR ENVELOPE
ENVELOPE 3,0,0,0,0 :'VOICE 3 MIN VALUES
FOR ENVELOPE
```
