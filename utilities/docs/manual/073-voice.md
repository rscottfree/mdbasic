---
name: VOICE
order: 73
token: auto
---


PURPOSE:

To set a frequency (pitch) for any voice
or to clear the SID registers.

SYNTAX:
```text

VOICE voice, frequency
VOICE CLR
```

DESCRIPTION:

VOICE is a dual function statement that
allows initialization of the SID chip
and setting the frequency (pitch) of a
voice. The SID chip provides three
separate oscillator channels called
voices. Each voice has 16-bit frequency
resolution, waveform control, envelope
shaping, oscillator synchronization, and
ring modulation. In addition, each voice
can be optionally routed to a
programmable filter to further enhance
the sound (See the FILTER statement).

There are 5 basic steps to produce
sounds:
1. Set the volume using the VOL
statement.
2. Select the frequency output using the
VOICE statement.
3. Set the envelope parameters using the
ENVELOPE statement.
4. Select the type of waveform and start
the desired part of the envelope cycle
using the WAVE statement.

voice (1-3) selects which voice will
have the frequency.

frequency (0.0 - 3994.966525 (NTSC-M) or
3848.59736 (PAL-B)) expressed in Hertz
(Hz), selects what the frequency output
of the voice. Fractional values can be
specified but the accuracy of the SID
chip is limited. This value can be
changed at any time to achieve special
sound effects.

VOICE CLR clears the registers that are
used to control the sounds for all three
voices. This is referred to as SID
initialization. When executed, all
sounds will be turned completely off,
and all 24 SID sound registers are set
to 0.

EXAMPLE:
```text

10 VOICE CLR :'INITIALIZE SID CHIP
20 VOICE 1,2000       :'VOICE 1 AT 2K HZ
30 ENVELOPE1,0,0,15,0 :'SUSTAIN VOLUME
TO MAX
40 VOL 15 :'SET VOLUME TO MAX
50 WAVE 1,1,1 :'START SOUND WITH
TRIANGLE WAVEFORM
```
