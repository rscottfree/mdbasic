---
name: PULSE
order: 50
token: auto
---


PURPOSE:

To set the pulse duty cycle for any of
the three voices.

SYNTAX:
```text

PULSE voice, duty
```

DESCRIPTION:

PULSE sets the pulse width of any voice.
This feature only works when a pulse
waveform has been selected, which the
output of the signal is a rectangular
wave.

voice (1-3) selects which voice to be
affected.

duty (0.0 to 100.0) determines the duty
cycle percentile of time that the
rectangular wave will stay at the high
part of the cycle. Changing the pulse
width will vastly change the sound
created when using the pulse waveform.

In order for this statement to affect
the sound, one of the pulse waveforms
(4,5,6 or 7) must be selected for the
corresponding voice by using the WAVE
statement. Refer to the WAVE statement
for details on selecting a waveform.

EXAMPLE:
```text
0 'PULSE 0 TO 100
5 SCREENCLR:PRINT"PULSE WIDTH: 0";
10 VOICECLR:VOL15
15 VOICE1,900
20 ENVELOPE1,0,0,15,0
25 WAVE1,4,1
30 FORI=0TO100:PULSE1,I
35 CURSOR12,0:PRINTI;:WAIT5
36 NEXT
50 WAVE1,4,0:WAIT20
55 VOICECLR
```
