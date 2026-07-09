; ***MDBASIC CTRL+RESTORE resident stub***
; The boot loader copies this image to $033c and repoints the cart NMI vector
; there. To stay clear of the common sprite-data poke at $0340-$037f, the only
; always-live code is the entry JMP at $033c and the real body at $0380+.
;
; The resident work stays compact:
;   * RESTORE / RUN-STOP+RESTORE gate
;   * SAVEONLY/CHOICE handoff for direct test entries
;   * copy a one-page launcher from the first tool bank's $9a00 to $0200
;   * jump there
;
; That launcher, running outside $c000, copies the menu-body UI to $c000, gets
; the user's choice, then launches the final pager/tool image over $c000 and
; does the single NMI-tail RTI.
;
; make_crt.py patches `firstbank` (offset 3, right after the opening JMP) with
; the actual first tool bank number; move/copy live in the next two banks.

R6510    = $01
CART     = $de00
STKEY    = $91        ;keyboard-matrix row 7 (STOP=bit7, CTRL=bit2), set by SCNSTOP
STOP     = $ffe1      ;kernal: test the STOP key (Z=1 if pressed)
SCNSTOP  = $f6bc      ;kernal: scan keyboard, STOP result in $91
REALGONE = $03f8      ;original runstp address (lo,hi), stashed by the loader
SAV01    = $05        ;saved $01
SAVEONLY = $0e        ;shared flag read by menu_body.asm's `start`: 0 = show the
                      ;full F1/R/M/C/STOP UI; nonzero = skip the UI and just save
                      ;screen/cursor/blink state before returning.
CHOICE   = $0f        ;direct-entry choice for tests (1 docs, 2 R, 3 M, 4 C)

*=$033c

 jmp start
firstbank .byte $ff   ;offset 3: first tool bank (renum/menu), patched by make_crt.py

*=$0380

start
 jsr SCNSTOP          ;scan keyboard for STOP
 jsr STOP             ;STOP key pressed too?
 beq tonormal         ;RUN/STOP+RESTORE -> original runstp (break)
 lda STKEY            ;CTRL held? bit 2 = 0 means pressed
 and #$04
 bne tonormal
 lda #0
 beq launch
tonormal
 jmp (REALGONE)       ;plain RESTORE -> original runstp (editor-mode reset / no-op)

;dodocs: launch the docs pager directly, bypassing the menu-body's full UI
;(but still running menu_body's quick save-only path first, via SAVEONLY, so the
;pager has a screen/cursor/blink snapshot to restore from at its own exit). This
;is what the F1 menu choice ultimately reaches too; tools/vice_docs_test.py SYSes
;here (past the CTRL/STOP gate) to exercise the pager without driving the menu.
dodocs
 lda #1
 bne direct
dorenum
 lda #2
 bne direct
domove
 lda #3
 bne direct
docopy
 lda #4
direct
 sta CHOICE
 lda #1
launch
 sta SAVEONLY
 lda R6510
 sta SAV01
 lda #$37
 sta R6510
 lda firstbank
 sta CART
 ldx #0
copylaunch
 lda $9a00,x
 sta $0200,x
 inx
 bne copylaunch
 lda #$80
 sta CART
 jmp $0200
