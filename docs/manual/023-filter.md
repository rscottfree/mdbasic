---
name: FILTER
order: 23
token: auto
---


PURPOSE:

To select filter settings of the Sound
Interface Adapter (SID) chip.

SYNTAX:
```text

FILTER [cutoff] [,resonance] [,type]
FILTER VOICE voice [,state]
```

DESCRIPTION:

The SID chip supports attenuation
(quieter) and amplification (louder) of
harmonic frequencies of waveforms from
any voice including the A/V port. There
is only one filter configuration which
can be enabled for any voice.

cutoff (30.0 – 11905.5 Hz) selects the
center frequency for making sound
quieter the further above and/or below
this frequency depending on the type of
filter used. SID voices (1-3) can only
go as high as 4KHz but voice 4 (input
from the AV port, pin 5), can be much
higher so the filter supports a higher
range.

resonance (0-15) allows peaking the
volume of harmonic frequencies nearest
the cutoff frequency which creates a
sharper filtering effect.

type (0-4) selects the type of filter
used with the center frequency:
0=no pass -mute entire oscillator output
1=low pass -suppress frequency
components above the cutoff frequency
2=band pass -suppress frequency
components above & below the cutoff
frequency
3=high pass -suppress frequency
components below the cutoff frequency
4=band stop -suppress frequency
components nearest the cutoff frequency

High & low pass filters attenuate the
volume of the frequency components
furthest away from the cutoff frequency
by 12dB per octave.

The band pass filter attenuates the
volume of the frequency components
furthest away from the cutoff frequency
by 6dB per octave.

The band stop (notch reject) filter
attenuates the volume of the frequency
components nearest the cutoff frequency
by 12dB per octave.

FILTER VOICE voice (1-4), [state: 0=off,
1=on (default)] controls the filtering
of a voice. Voice 4 is the external
input on pin 5 of the A/V port.

EXAMPLE:
```text
FILTER 1200.5,15,1 :'LOW PASS,
CUTOFF=1200.5HZ, RESONANCE 15
FILTER 500 :'JUST CHANGE THE
CUTOFF/CENTER FREQUENCY
FILTER ,0 :'JUST TURN OFF RESONANCE
FILTER VOICE 4 :'APPLY FILTER ON
EXTERNAL INPUT OF A/V PORT PIN 5
```
