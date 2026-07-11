---
name: ROUND()
order: 55
token: auto
---


PURPOSE:

To round a floating point number to a
specified precision.

SYNTAX:
```text

N = ROUND(float [,precision])
```

DESCRIPTION:

ROUND is a numeric function that returns
the given value rounded to a specified
number of decimal places. ROUND is
useful for correcting inaccuracies with
single-precision, floating-point
numbers.

float is a floating-point variable (or
constant) of the number to round.

precision (optional, signed integer -9
to 9 default 0) is the number of digits
left (negative) or right (positive) of
the decimal point. If no precision is
specified the default is 0 which returns
the nearest whole number value. When
precision is negative, the whole number
portion will be rounded to the nearest
number's place. For example: -1 is tens
place, -2 is hundreds place, etc.

There are limitations to accuracy that
can produce incorrect rounding results.
The 32-bit binary representation uses
the same bits for the whole number
portion and the fractional portion. A
smaller whole number value can have more
fractional digits and vise-versa.
Accuracy problems can occur with numbers
that have a large whole number and
fractional portion. However, values that
are between -999999.000 and 999999.000
rounded with precision between 0 and 3
should be accurate and cover most use
cases.

EXAMPLE:
```text

PRINT
ROUND(5.0125),ROUND(5.0125,0),ROUND(5.0125,2),ROUND(5.0125,3)
5         5         5.01      5.013

PRINT
ROUND(125.23),ROUND(125.23,-1),ROUND(125.23,-2),ROUND(125.23,-3)
125       130       100      0
```
