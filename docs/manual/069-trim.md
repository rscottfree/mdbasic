---
name: TRIM()
order: 69
token: auto
---


PURPOSE:

To return the value of a signed 32-bit
single-precision floating-point number
with its fractional portion removed
(truncated).

SYNTAX:
```text
I = TRIM(n)
```

DESCRIPTION:

TRIM returns the whole number (integer)
portion of a signed 32-bit floating-
point decimal number. This differs from
the INT function which returns the
lowest (floor) integer value. See the
examples below which demonstrates this
concept.

n is the 32-bit, single-precision,
signed floating-point decimal number to
remove (truncate) the fractional
portion. If the data type of this
parameter is an integer then the result
is a float with the same value
(unchanged).

To obtain the fractional portion of a
number simply subtract the trimmed
portion from the original portion as
demonstrated in the example below. The
ROUND function can be used to correct
inaccuracies due to the use of
single-precision floating-point numbers.

EXAMPLE:
```text

'TRUNCATE VS FLOOR ON NEGATIVE VALUE
N=-4.25 : PRINT TRIM(N), INT(N)
-4        -5

'GET FRACTIONAL PORTION
N=11.0625 : PRINT A-TRIM(N)
.0625

'GET FRACTIONAL PORTION WHEN PRECISION
LOSS OCCURS
N=104.0125 : F=N-TRIM(N) : PRINT F,
ROUND(F,4)
.0124999881         .0125

10 'PERFORM X MOD Y CALCULATION
20 X=25 : Y=12
30 M = X-TRIM(X/Y)*Y
40 PRINT X;"MOD";Y;"=";M
```
