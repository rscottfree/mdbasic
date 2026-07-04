---
name: VALB(), VALH(), VALO()
order: 71
token: none
---


PURPOSE:

To provide decimal conversion of string
values in base 2, 8 or 16.

SYNTAX:
```text

B = VALB(binary$)
H = VALH(hexadecimal$)
O = VALO(octal$)
```

DESCRIPTION:

These functions are similar to VAL
function for converting numbers stored
in a string to its numeric decimal
value. Zero is returned if conversion
fails.

The string parameter (binary$,
hexadecimal$, octal$) represents the
value with a specific base to be
converted to a 32-bit decimal number.
The conversion stops at the end of the
string or the first invalid character
for the base. All spaces are ignored.
Below is the list of string-to-value
conversions.

FUNCTION BASE BASE NAME PARAMETER VALUE
EXAMPLES*
VALB 2 Binary "1", "11001",
"1100000000000000"
VALO 8 Octal "1", "31", "140000"
VAL 10 Decimal "1", "25", "49152"
VALH 16 Hexadecimal "1", "19", "C000"

*In the table above, the parameter value
examples will all result in decimal
values 1, 25, 49152 respectively.

To convert decimal to hexadecimal use
the HEX$() function, for example:
H$ = HEX$(10)

For literal values in a BASIC program,
prefix the value with the associated
symbol: % (binary), @ (octal) and $
(hexadecimal). For example:
SYS $FFD2,$41 : PRINT %101010100110 : O
= @77

NOTE: MDBASIC does not provide a
function to convert a decimal value to a
binary or octal string.

EXAMPLE:
```text

PRINT VALH("FCE2"), VALB("1000"),
VALO("30")
64738    8        24
```
