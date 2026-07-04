---
name: WAVE
order: 76
token: auto
---


PURPOSE:

To select a waveform for a SID voice and
start an envelope cycle.

SYNTAX:
```text

WAVE voice, waveform [,gate [,sync
[,ring [,disable]]]]
```

DESCRIPTION:

WAVE is primarily used to select a
waveform for a voice and start an
envelope cycle. It also provides
oscillator synchronization and ring
modulation. It can also completely
disable a voice oscillator. The optional
parameters (gate, sync, ring, disable)
are cumulatively required and default to
0 when omitted.

voice (1-3) is the voice to apply the
waveform settings.

waveform (0-8) selects the waveform for
the voice. Each waveform contains
varying harmonic content that affects
the tone quality of the sound. The
waveforms available are as follows:

| VALUE | WAVEFORM |
|--|--|
| 0 | none |
| 1 | triangle |
| 2 | saw tooth |
| 3 | saw tooth + triangle |
| 4 | pulse |
| 5 | pulse + triangle |
| 6 | pulse + saw tooth |
| 7 | pulse + saw tooth + triangle |
| 8 | noise |

Refer to the PULSE statement for setting
the duty cycle of the pulse waveform.

gate (1 or 0, default 0) is a Boolean
expression used to start one of the two
envelope cycles. The first part of the
envelope is the Attack, Decay, Sustain
cycle. When gate is set to 1, the output
of the selected voice will follow its
envelope settings. After rising to a
peak and declining to the sustain
volume, the volume will continue at the
sustain level until gate is set to 0,
which starts the release cycle. Thus,
gate has two functions:
1 = start the attack/decay/sustain cycle
0 = start the release cycle

Refer to the ENVELOPE statement for to
configure a voice envelope.

sync (1 or 0, default 0) is a Boolean
expression used to synchronize the
fundamental frequency of the specified
voice with its associated sync voice,
allowing the creation of complex
harmonic structures from the selected
voice. When enabled, the synchronized
voice's frequency affects the output of
the selected voice. The following is the
synchronization combinations:
a. Voice 1 syncs with voice 3
b. Voice 2 syncs with voice 1
c. Voice 3 syncs with voice 2

ring (1 or 0, default 0) is a Boolean
expression used to replace the triangle
waveform with a ring modulated
combination of the specified voice with
its associated ring voice. This produces
non-harmonic overtone structures that
are useful for creating bell or gong
sound effects. The voice selected can
ring with one other voice as follows:
a. Voice 1 rings with voice 3
b. Voice 2 rings with voice 1
c. Voice 3 rings with voice 2

disable (1=disable, 0=enable, default 0)
is a Boolean expression used to disable
the oscillator of the selected voice.
This can be useful when generating very
complex waveforms like those used for
speech synthesis.

EXAMPLE:
```text

WAVE 1,1 :'VOICE 1 HAS A TRIANGLE
WAVEFORM
WAVE 3,0,0,0,0,1 :'DISABLE VOICE 3
OSCILLATOR
WAVE 3,2,1 :'VOICE 3 HAS A SAW TOOTH
WAVEFORM; START ADS CYCLE

0 'SIREN SOUND
10 VOICECLR:VOL15
20 VOICE1,900
25 ENVELOPE1,5,0,15,5
30 WAVE1,1,1
40 FORI=800TO1000:VOICE1,I:NEXT
50 WAIT10
60 FORI=1000TO800STEP-1:VOICE1,I:NEXT
70 C=C+1:IFC<2THEN40
75 WAVE1,1,0:WAIT20
80 VOICECLR
```
