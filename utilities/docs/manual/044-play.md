---
name: PLAY
order: 44
token: auto
---


PURPOSE:

To play musical notes on any one of the
three available SID voices.

SYNTAX:
```text

PLAY S$
PLAY OFF
```

DESCRIPTION:

The PLAY statement uses any voice to
play real musical notes at eight
different octaves (see Appendix E) in
foreground or background mode. If the
main volume is currently set to 0 then
it will automatically be set to the
maximum of 15.

S$ is the string of notes to play.
Invalid characters and notes will be
ignored.

There are 7 primary notes (A to G) in
each of the eight octaves. Sharps (# or
+) and Flats (-) can be used to play the
notes between notes like the black keys
on a piano. Below is the table of
symbols available to play music:

<!-- table: mode=sections -->
| SYMBOL | MEANING |
|--|--|
| ! | Play notes in foreground (must be first character in string) |
| @ | Start over from beginning (should be last character in string) |
| A-G[#\|+\|-][n] | Musical note to play with optional length n jiffies |
| Ln | Length n (0-99, default 30) in jiffies for all notes |
| On | Octave n (0-7, default 4) for all notes |
| < \| > | Decrease or increase the current octave number by 1 |
| P[n] | Pause play for length n (0-99, default 30) jiffies |
| S[n] | Sustain volume n (0-15, default 15) for all notes |
| Vn | Voice n (1-3, default 1) for all notes |
| Wn | Waveform n (0-8, default 4 @ 50% duty) for all notes. Refer to the WAVE statement for available waveforms |

PLAY OFF will abort notes that are
playing in background mode (if any).

EXAMPLE:
```text
PLAY "!V3W1L20 A-A A#10 B-CC# P
DD#EFF#GG# > A-AA#10B-CC# P60
DD#EFF#GG#"
```
