---
name: SWAP
order: 64
token: auto
---


PURPOSE:

To exchange the values of two variables
of the same data type.

SYNTAX:
```text

SWAP variable1, variable2
```

DESCRIPTION:

The SWAP statement efficiently exchanges
the values of two variables. This
eliminates the need of a third variable
to make the swap. String variables are
exchanged by simply swapping the string
pointers of both variables. SWAP is very
useful in algorithms that sort array
data.

variable1 is the first variable name
that will be exchanged.

variable2 is the second variable name
that will be exchanged.

variable1 & variable2 must be of equal
type, such as floating point to floating
point, integer to integer, string to
string. If the variables are of
different types, a TYPE MISMATCH ERROR
will occur.

EXAMPLE:
```text

SWAP A,B :'A & B EXCHANGE NUMERIC VALUES
SWAP A$(1),A$(2) :'A$(1) & A$(2)
EXCHANGE STRING VALUES
SWAP X%,Y% :'X% & Y% EXCHANGE NUMERIC
VALUES
SWAP N$,K$ :'N$ & K$ EXCHANGE STRING
VALUES
```
