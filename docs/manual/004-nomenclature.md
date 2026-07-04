---
name: NOMENCLATURE
order: 4
token: none
---


Direct and Indirect Mode
In direct mode BASIC statements and
commands are executed immediately after
they are entered on the keyboard.
Various uses include performing
arithmetic calculations or executing
operations on the disk drive. The
commands entered are not stored and any
variable data is lost when executing a
program. Indirect mode is used when
entering a program into memory. One or
more statements are entered preceded by
a line number. The statements are
executed using the RUN command. Be sure
to save your programs to disk before
running newly entered programs.

Keywords, Commands, Statements and
Tokens
All these words are essentially
referring to the same thing. Keywords
are reserved words that cannot be used
as a variable. All commands and
statements are keywords. When a
statement is entered in direct mode it
is referred to as a command as it
immediately does what you ask. A
statement refers to the use of a command
in a program. BASIC programs have a
binary storage format which uses less
space than plain text and executes
faster. This is due to the assignment of
a single-byte token for each keyword.

Variables, Constants and Literals
A variable is a name given to a known
numeric or string value and can be
changed at anytime in a running program.
Constants are values that do not change.
CBM BASIC does not differentiate between
named variables and constants. It is the
responsibility of the programmer to know
which variable names are used as
constants and which are variables.
Literals are constants without a name.
The value is embedded in the program
code thus it does not change and
therefore must be repeatedly entered
when referenced throughout the program.

Expressions and Operations
An expression is one or more variable,
constant or literal values of compatible
data types combined with operators to
yield a single result.

An operation is a process performed on
an expression to yield a single result.
Operations are performed in a specific
order. Parentheses can be used to group
expressions to ensure a specific order.
The arithmetic order of operations is
Parenthesis, Exponents, Multiplication,
Division, Addition, Subtraction.

Below are the four types of operations
with examples:
1. Arithmetic: +, -, *, /, ^
2. Logical: AND, OR, NOT
3. Relational: =, <, >, <=, >=, <>
4. Functional: EXP(n), SIN(n), STR$(n),
VAL(s$), LEFT$(s$,n), etc.
