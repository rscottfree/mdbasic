---
name: USER REF. GUIDE
order: 5
token: none
---


Introduction
This section of the manual contains an
alphabetical list of commands,
statements, functions and variables.
Each one is described in detail using
the following format:

✔ Purpose A short summary describing the
reason for the instruction

✔ Syntax Generic variations of how the
keywords and parameters are used

✔ Description A detailed explanation of
the instruction and parameters

✔ Example One or more examples of the
instruction

Documentation of Syntax
Each command/statement in this document
uses a specific structure to indicate
the parameters available and if they are
required or optional. Required
parameters will cause a SYNTAX ERROR if
not present. Optional parameters can be
omitted or skipped depending on the
statement and may use a default value.
The space between commands and
parameters is optional and provided for
readability. The name of the parameters
are also for readability. Actual
variable names are limited to only 2
characters.

This document makes use of brackets []
to denote an optional parameter(s). The
brackets are not to be entered into the
program. When skipping over parameters
the comma for each skipped value must be
present. When omitting the rest of the
optional parameters the statement can be
ended normally. For example:

FILTER [freq] [,resonance] [,type]

All parameters are optional but at least
one must be specified because there are
no default values to apply. Statements
like the FILES command can omit all
parameters since default values are
applied for each omitted parameter
(volume$="", device=8).

DISK dos$ [,device [,result$]]

The first parameter is a string and is
required. The next two parameters are
optional. If the second parameter is
supplied then the third parameter can be
omitted. The third parameter requires
the first two parameters. The following
statements are valid syntax based on
this definition:

DISK V$ : DISK V$,8 : DISK V$,8,S$

The pipe symbol is used to denote
alternate syntax. The example below
indicates more than one syntax, AUTO ON
or AUTO OFF.

AUTO ON | OFF
