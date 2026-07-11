---
name: APPENDIX D: RS-232
order: 80
token: none
---

RS-232 STATUS CODES

The status of RS-232 data port can be
determined by using the CBM BASIC
reserved variable ST. This variable will
be set to 0 after it is read so you if
need to use it more than once then store
the result in another variable and use
that variable for analysis. The status
value is described below:

Bit 7: 1 = (128) Break Detected
Bit 6: 1 = (64) DTR (Data Set Ready)
Signal Missing
Bit 5: Unused
Bit 4: 1 = (16) CTS (Clear to Send)
Signal Missing
Bit 3: 1 = (8) Receiver Buffer Empty
Bit 2: 1 = (4) Receiver Buffer Overrun
Bit 1: 1 = (2) Framing Error
Bit 0: 1 = (1) Parity Error

The user is responsible for checking the
status and taking appropriate action.
If, for example, you find that Bit 0 or
1 is set when you are sending,
indicating a framing or parity error,
you should resend the last byte. If Bit
2 is set, the SERIAL READ statement is
not being executed fast enough to empty
the buffer. MDBASIC should be able to
keep up at 1200 baud safely, 2400 max.
If Bit
7 is set, you will want to stop sending,
and execute SERIAL READ to see what is
being sent.

The limitations of the communication
speed on the serial port is due to the
implementation of the buffered
read/write process that is driven by an
IRQ handler.
