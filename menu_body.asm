; ***MDBASIC CTRL+RESTORE menu-body UI***
; Drawn/run at $c000 (copied there from RENUM_BANK $8c00 by the $033c stub in
; menu.asm). Draws a one-line prompt on screen row 24, reads one key, restores
; the row, and returns the choice in X:  0 = dismiss, 1 = docs pager, 2 = renum.
;
; This runs BEFORE any tool is launched (the stub copies the chosen tool over
; $c000 afterwards), so it is free to live in the tool region. It points the
; func-key decode vector back at the kernal standard for the read (MDBASIC
; otherwise expands F1/F3 to KEY strings) and restores it before returning, so
; the tool that follows sees the user's real KEYLOG hook.
;
; Assembled for $c000 (run location).

R6510    = $01        ;set to $37 by the stub before entry (I/O + KERNAL in)
QTSW     = $d4        ;editor quote-mode flag
RVS      = $c7        ;editor reverse flag
INSRT    = $d8        ;editor insert count
KEYLOG   = $028f      ;keyboard decode-table setup vector (MDBASIC hooks this)
STDKEYLOG = $eb48     ;kernal's standard decode-table setup (raw F1-F8 codes)
GETIN    = $ffe4      ;kernal: read one key from the buffer (A=0 if none)
PROMPTROW = $07c0     ;screen RAM row 24 (bottom line)
KEY_F1   = $85
KEY_F3   = $86
KEY_STOP = $03

*=$c000

 lda KEYLOG           ;save + retarget the func-key decode vector
 sta svkey
 lda KEYLOG+1
 sta svkey+1
 lda #<STDKEYLOG
 sta KEYLOG
 lda #>STDKEYLOG
 sta KEYLOG+1
 lda #0               ;clear any active editor mode so the resumed editor is clean
 sta QTSW
 sta INSRT
 sta RVS
 ldx #PROMPTLEN-1     ;save row 24 and draw the prompt over it
draw
 lda PROMPTROW,x
 sta svrow,x
 lda prompt,x
 and #$3f             ;PETSCII -> screen code for our uppercase/space/digit/'=' set
 sta PROMPTROW,x
 dex
 bpl draw
 cli                  ;let the kernal IRQ scan the keyboard for GETIN
keyloop
 jsr GETIN
 ldx #1
 cmp #KEY_F1
 beq chosen
 ldx #2
 cmp #KEY_F3
 beq chosen
 ldx #0
 cmp #KEY_STOP
 bne keyloop          ;ignore any other key
chosen
 stx svchoice
 sei
 ldy #PROMPTLEN-1     ;restore row 24
rrow
 lda svrow,y
 sta PROMPTROW,y
 dey
 bpl rrow
 lda svkey            ;restore MDBASIC's func-key decode hook
 sta KEYLOG
 lda svkey+1
 sta KEYLOG+1
 ldx svchoice
 rts

prompt .text "F1=DOCS F3=RENUM STOP=QUIT"
PROMPTLEN = *-prompt
svrow .repeat 40,0    ;scratch (copied from the bank as zeros, written at runtime)
svkey .word 0
svchoice .byte 0
