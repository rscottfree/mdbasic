---
name: APPENDIX E: NOTES
order: 81
token: none
---

Musical Notes Chart
This is a list of notes in the
order that they appear on an 88-
key piano, which is also the
order of the frequency in Hertz
and octave order (0-7). Key 1 is
the left-most key and 88 is the
right-most key.

The PLAY statement produces
these notes based on this table
with Middle-C (C4) selecting the
default octave (4). Refer to
the PLAY statement for details.

MDBASIC detects the type of
system clock NTSC (1.02 MHz) or
PAL (0.985 MHz) and calculates
the frequency accordingly.

The first note on any octave is
C, followed by D, E, F, G, A, B.
This sequence of notes will have
an increasing frequency. Sharps
are a half-step up in frequency.
Flats are derived from sharps
and are a half-step down.

Invalid character sequences will
be ignored. For example, there
is no such note as B# or C- or
E# or F-. All punctuation and
spaces will be ignored. Octave
numbers greater than 7 will be
ignored. Play lengths are
limited to 2 digits (99) so
additional digits are ignored.

PLAY will stop any notes or
sound playing on the specified
voice number (default 1) before
processing the string of notes.
All notes are affected by the
current filter configuration
defined by the last FILTER
statement, which can be changed
while notes are playing in the
background.

MUSICAL NOTES CHART (88-KEY PIANO)

<!-- table: mode=sections -->
| KEY / NOTE | FREQUENCY | HELMHOLTZ | ALSO | OPEN STRINGS |
|--|--|--|--|--|
| 88  C8 | 4186.01 Hz | c''''' | Eighth octave / 5-line octave |  |
| 87  B7 | 3951.07 Hz | b'''' |  |  |
| 86  A#7/Bb7 | 3729.31 Hz | a#''''/bb'''' |  |  |
| 85  A7 | 3520.00 Hz | a'''' |  |  |
| 84  G#7/Ab7 | 3322.44 Hz | g#''''/ab'''' |  |  |
| 83  G7 | 3135.96 Hz | g'''' |  |  |
| 82  F#7/Gb7 | 2959.96 Hz | f#''''/gb'''' |  |  |
| 81  F7 | 2793.83 Hz | f'''' |  |  |
| 80  E7 | 2637.02 Hz | e'''' |  |  |
| 79  D#7/Eb7 | 2489.02 Hz | d#''''/eb'''' |  |  |
| 78  D7 | 2349.32 Hz | d'''' |  |  |
| 77  C#7/Db7 | 2217.46 Hz | c#''''/db'''' |  |  |
| 76  C7 | 2093.00 Hz | c'''' | Double high C / 4-line octave |  |
| 75  B6 | 1975.53 Hz | b''' |  |  |
| 74  A#6/Bb6 | 1864.66 Hz | a#'''/bb''' |  |  |
| 73  A6 | 1760.00 Hz | a''' |  |  |
| 72  G#6/Ab6 | 1661.22 Hz | g#'''/ab''' |  |  |
| 71  G6 | 1567.98 Hz | g''' |  |  |
| 70  F#6/Gb6 | 1479.98 Hz | f#'''/gb''' |  |  |
| 69  F6 | 1396.91 Hz | f''' |  |  |
| 68  E6 | 1318.51 Hz | e''' |  | Guitar High E (24th Fret) |
| 67  D#6/Eb6 | 1244.51 Hz | d#'''/eb''' |  |  |
| 66  D6 | 1174.66 Hz | d''' |  |  |
| 65  C#6/Db6 | 1108.73 Hz | c#'''/db''' |  |  |
| 64  C6 | 1046.50 Hz | c''' | Soprano C (High C) / 3-line octave |  |
| 63  B5 | 987.767 Hz | b'' |  |  |
| 62  A#5/Bb5 | 932.328 Hz | a#''/bb'' |  |  |
| 61  A5 | 880.000 Hz | a'' |  |  |
| 60  G#5/Ab5 | 830.609 Hz | g#''/ab'' |  |  |
| 59  G5 | 783.991 Hz | g'' |  |  |
| 58  F#5/Gb5 | 739.989 Hz | f#''/gb'' |  |  |
| 57  F5 | 698.456 Hz | f'' |  |  |
| 56  E5 | 659.255 Hz | e'' |  | Violin E |
| 55  D#5/Eb5 | 622.254 Hz | d#''/eb'' |  |  |
| 54  D5 | 587.330 Hz | d'' |  |  |
| 53  C#5/Db5 | 554.365 Hz | c#''/db'' |  |  |
| 52  C5 | 523.251 Hz | c'' | Tenor C / 2-line octave |  |
| 51  B4 | 493.883 Hz | b' |  |  |
| 50  A#4/Bb4 | 466.164 Hz | a#'/bb' |  |  |
| 49  A4 | 440.000 Hz | a' | A440 | Violin A, Viola A, Guitar High A (Optional) |
| 48  G#4/Ab4 | 415.305 Hz | g#'/ab' |  |  |
| 47  G4 | 391.995 Hz | g' |  |  |
| 46  F#4/Gb4 | 369.994 Hz | f#'/gb' |  |  |
| 45  F4 | 349.228 Hz | f' |  |  |
| 44  E4 | 329.628 Hz | e' |  | Guitar High E |
| 43  D#4/Eb4 | 311.127 Hz | d#'/eb' |  |  |
| 42  D4 | 293.665 Hz | d' |  | Violin D, Viola D |
| 41  C#4/Db4 | 277.183 Hz | c#'/db' |  |  |
| 40  C4 | 261.626 Hz | c' | Middle C / 1-line octave |  |
| 39  B3 | 246.942 Hz | b |  | Guitar B |
| 38  A#3/Bb3 | 233.082 Hz | a#/bb |  |  |
| 37  A3 | 220.000 Hz | a |  | Cello A |
| 36  G#3/Ab3 | 207.652 Hz | g#/ab |  |  |
| 35  G3 | 195.998 Hz | g |  | Violin G, Viola G, Guitar G |
| 34  F#3/Gb3 | 184.997 Hz | f#/gb |  |  |
| 33  F3 | 174.614 Hz | f |  | Bass F (7 string) |
| 32  E3 | 164.814 Hz | e |  |  |
| 31  D#3/Eb3 | 155.563 Hz | d#/eb |  |  |
| 30  D3 | 146.832 Hz | d |  | Cello D, Guitar D |
| 29  C#3/Db3 | 138.591 Hz | c#/db |  |  |
| 28  C3 | 130.813 Hz | c | Low C / small octave | Violin C (5 string), Viola C, Bass C (6 string) |
| 27  B2 | 123.471 Hz | B |  |  |
| 26  A#2/Bb2 | 116.541 Hz | A#/Bb |  |  |
| 25  A2 | 110.000 Hz | A |  | Guitar A |
| 24  G#2/Ab2 | 103.826 Hz | G#/Ab |  |  |
| 23  G2 | 97.9989 Hz | G |  | Cello G, Bass G |
| 22  F#2/Gb2 | 92.4986 Hz | F#/Gb |  |  |
| 21  F2 | 87.3071 Hz | F |  | Violin F (6 string) |
| 20  E2 | 82.4069 Hz | E |  | Guitar Low E |
| 19  D#2/Eb2 | 77.7817 Hz | D#/Eb |  |  |
| 18  D2 | 73.4162 Hz | D |  | Bass D |
| 17  C#2/Db2 | 69.2957 Hz | C#/Db |  |  |
| 16  C2 | 65.4064 Hz | C | Deep C / great octave | Cello C |
| 15  B1 | 61.7354 Hz | B, |  | Guitar B (7 string) |
| 14  A#1/Bb1 | 58.2705 Hz | A#,/Bb, |  | Violin Bb (7 string) |
| 13  A1 | 55.0000 Hz | A, |  | Bass A |
| 12  G#1/Ab1 | 51.9131 Hz | G#,/Ab, |  |  |
| 11  G1 | 48.9994 Hz | G, |  |  |
| 10  F#1/Gb1 | 46.2493 Hz | F#,/Gb, |  | Guitar F# (8 string) |
| 9  F1 | 43.6535 Hz | F, |  |  |
| 8  E1 | 41.2034 Hz | E, |  | Bass E |
| 7  D#1/Eb1 | 38.8909 Hz | D#,/Eb, |  |  |
| 6  D1 | 36.7081 Hz | D, |  |  |
| 5  C#1/Db1 | 34.6478 Hz | C#,/Db, |  |  |
| 4  C1 | 32.7032 Hz | C, | Pedal C / contra-octave |  |
| 3  B0 | 30.8677 Hz | B,, |  | Bass B (5 string) |
| 2  A#0/Bb0 | 29.1352 Hz | A#,,/Bb,, |  |  |
| 1  A0 | 27.5000 Hz | A,, | Double Pedal A / sub-contra-octave |  |
