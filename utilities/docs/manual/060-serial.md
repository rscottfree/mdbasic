---
name: SERIAL
order: 60
token: auto
---


PURPOSE:

To send and receive data through the
RS-232 port.

SYNTAX:
```text

SERIAL OPEN [baudrate] [,databits]
[,stopbits] [,duplex] [,parity]
[,handshake]
SERIAL [WAIT [timeout]] READ variable
[TO sentinel]
SERIAL PRINT [expression]
SERIAL CLOSE
```

DESCRIPTION:

The SERIAL statement is a
multi-functional command used to execute
multiple operations on the RS-232 port.
SERIAL must be followed by of of the
keywords OPEN, READ, PRINT and CLOSE.
The benefits of using SERIAL is speeding
up the read process to keep up with
higher baud rates. Also, SERIAL will not
cause variable data loss or BASIC memory
reduction as occurs with opening device
2 with OPEN. These statements can also
be used in direct mode if needed.

SERIAL OPEN is used to open the RS-232
channel for communication. If the port
is already open the FILE OPEN ERROR will
result.

baudrate (optional, default 1200) is the
speed for bit transmission. The value
must be 50, 75, 110, 134, 150, 300, 600,
1200, 1800 or 2400 otherwise an ILLEGAL
QUANTITY ERROR will result.

databits (optional, 5, 6, 7 or 8,
default 8) is the number of bits that
make up the packet for one "word" of
data. Some data, like ASCII characters
do not need all 8 bits so it is better
to reduce the size to increase overall
throughput.

stopbits (optional, 0 or 1, default 0)
is the number of bits used to provide
markers in the transmission to demark
the end of a packet of data (byte).

duplex (optional, 0 = full (default), 1
= half) controls the synchronization of
data flow. Full duplex allows
simultaneous send & receive transmission
(like a telephone). Half duplex is one
direction at a time (like a walkie
talkie).

parity (optional, 0-4, default 0)
controls how data packet errors are
detected.

| PARITY | DESCRIPTION |
|--|--|
| 0 | No Parity Generated or Received |
| 1 | Odd Parity Transmitted and Received |
| 2 | Even Parity Transmitted and Received |
| 3 | Mark Parity Transmitted and Received |
| 4 | Space Parity Transmitted and Received |

handshake (0 = 3-Line (default), 1 =
X-Line) is the signal (CTS/RTS) control
of the transmission of data to help
prevent data loss between a fast sender
and a slow receiver.

SERIAL WAIT will suspend the program
until the next byte of data is read. The
time to wait is infinite unless a
timeout is provided. When reading data
into strings, each byte received resets
the timeout.

timeout (optional, 0-65535 jiffies)
indicates how many jiffies to wait for
the next byte in the buffer before
ending the read. If timeout is 0 or
omitted then the wait will be infinite.

variable is the variable that will
receive the result of the read. Numeric
data types (float or integer) will only
capture one byte at a time. Your program
must have a loop to read each byte which
is slower and may result in buffer
overrun at higher baud rates. When the
variable is a string, multiple bytes can
be read in the same READ statement which
is much faster. Note that binary data
may have zero-byte values included in
the string. If the amount of data
exceeds 255 bytes then the string is
returned, thus another read must be used
to get more data.

sentinel is the byte which will stop the
read and return the result which
includes the sentinel byte itself. If
the variable is numeric, all bytes up to
the sentinel are discarded (skipped). If
the variable is a string and the results
reaches 255 bytes or the timeout is
reached then the data is returned
regardless of the presence of the
sentinel. In this case an empty string,
or a zero numeric value depending on the
data type of the variable, will be
returned. You can use the CBM BASIC
variable ST to determine the status.

SERIAL READ will read a maximum of 255
bytes or up to an optionally specified
stopping byte (sentinel), whichever
condition comes first. The first read
after opening the port will adjust for
the start bit automatically.

SERIAL PRINT can be used to send data.
The syntax is exactly like any PRINT
statement. You can end the expression
with a semicolon to prevent sending a
carriage return character.

SERIAL CLOSE is used to finalize the
communication on the RS-232 port. You
must use CLOSE to change the parameters
of the opened channel. Like CBM BASIC’s
CLOSE statement, SERIAL CLOSE will never
cause an error even if it wasn’t opened.

The ST variable can be used to determine
the status of the last SERIAL READ. Be
aware that the value of the ST variable
will be cleared after reading its value
so you may need to capture the value in
your own variable if you need to refer
to it more than once. See Appendix D for
details of the status code.

See Appendix G for a more detailed
example.

EXAMPLE:
```text

SERIAL OPEN :'OPEN RS-232 CHANNEL WITH
USE DEFAULTS
SERIAL WAIT 300 READ S$ :'READ A STRING
OF BYTES WITH 5 SEC TIMEOUT
SERIAL PRINT A$; :'WRITE A STRING
WITHOUT CARRIAGE RETURN
SERIAL CLOSE :'CLOSE THE CHANNEL
```
