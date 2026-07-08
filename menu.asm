; ***MDBASIC CTRL+RESTORE utility menu -- $033c stub***
; Freeze-cartridge style trigger: pressing CTRL+RESTORE shows a tiny function-key
; menu that launches the docs pager (F1) or the renumber/move tool (F3).
;
; The boot loader copies this stub from cart bank 3 ($9800) to $033c (cassette
; buffer), stashes the image's original runstp (RESTORE/NMI) address at REALGONE,
; and patches the image's cart NMI vector ($8002) to point here. The KERNAL
; cart-NMI path then jumps ($8002) -> here on every RESTORE. This code is reached
; ONLY on a RESTORE press -- never on the normal execution path -- so it cannot
; disturb running programs.
;
;   CTRL + RESTORE       -> show the F1/F3 menu (F1 docs pager, F3 renum tool,
;                           RUN/STOP dismisses).
;   RESTORE alone        -> the original runstp behaviour (editor-mode reset).
;   RUN/STOP + RESTORE   -> the original runstp behaviour (break), via REALGONE.
;
; CTRL is detected for free: SCNSTOP scans keyboard-matrix row 7 into STKEY ($91)
; for the STOP test, and CTRL shares that row (STOP = bit 7, CTRL = bit 2; 0 =
; pressed). So no IRQ keyscan / SHFLAG dependence -- works even with IRQs masked.
;
; Because the whole menu (prompt draw + key read + the tool copy loop) does NOT
; fit in the ~188 free bytes below REALGONE, this stub stays minimal: it uses one
; shared `copyrun` helper (bank -> $c000 -> JMP) to first run the menu-body UI
; (RENUM_BANK $8c00, drawn at $c000, returns the choice), then to copy+run the
; chosen tool (also at $c000, over the now-defunct menu-body). Each tool RTSs back
; here and this stub does the single NMI-tail RTI. See renum-move-tool-plan.
;
; make_crt.py patches `renumbank` (fixed offset 3, right after the opening JMP)
; with the actual RENUM_BANK number, which varies with the doc-data bank count.

R6510    = $01
CART     = $de00
STKEY    = $91        ;keyboard-matrix row 7 (STOP=bit7, CTRL=bit2), set by SCNSTOP
STOP     = $ffe1      ;kernal: test the STOP key (Z=1 if pressed)
SCNSTOP  = $f6bc      ;kernal: scan keyboard, STOP result in $91
NMIRTI   = $fe72      ;kernal NMI tail: pops A/X/Y and RTIs to the interrupted code
INDEX_BANK = 3        ;docs pager code lives at bank 3 $8000
REALGONE = $03f8      ;original runstp address (lo,hi), stashed by the loader
;--- zero-page scratch for copyrun (safe during the RESTORE NMI) ---
SRCZP    = $fb
DSTZP    = $fd
CPPAGES  = $02        ;copyrun page counter
CPSRC    = $03        ;copyrun source page hi
CPDST    = $04        ;copyrun dest page hi
SAV01    = $05        ;saved $01

*=$033c

 jmp start
renumbank .byte $ff   ;offset 3: RENUM_BANK, patched by make_crt.py
start
 jsr SCNSTOP          ;scan keyboard for STOP
 jsr STOP             ;STOP key pressed too?
 beq tonormal         ;RUN/STOP+RESTORE -> original runstp (break)
 lda STKEY            ;CTRL held? bit 2 = 0 means pressed
 and #$04
 beq domenu           ;CTRL+RESTORE -> show the menu
tonormal
 jmp (REALGONE)       ;plain RESTORE -> original runstp (editor-mode reset / no-op)

;dodocs: launch the docs pager directly, bypassing the menu-body. This is the
;exact code the F1 menu choice runs; tools/vice_docs_test.py SYSes here (past the
;CTRL/STOP gate) to exercise the pager without driving the menu.
dodocs
 lda R6510
 sta SAV01
 lda #$37
 sta R6510
 jmp lpager

;dorenum: launch the renum tool directly (same as the F3 menu choice); used by
;tools/vice_renum_test.py to reach the tool without driving the menu-body.
dorenum
 lda R6510
 sta SAV01
 lda #$37
 sta R6510
 jmp lrenum

domenu
 lda R6510
 sta SAV01
 lda #$37
 sta R6510            ;BASIC+KERNAL+I/O in, cart visible at $8000
 ;run the menu-body UI: RENUM_BANK $8c00 -> $c000, returns X = choice (0/1/2)
 lda #$8c
 sta CPSRC
 lda #$c0
 sta CPDST
 lda renumbank
 ldx #2               ;2 pages is ample for the menu-body UI
 jsr copyrun
 cpx #1
 beq lpager
 cpx #2
 beq lrenum
 jmp fin              ;0 = dismissed, launch nothing
lpager
 lda #INDEX_BANK      ;docs pager: bank 3 $8000
 bne launchtool
lrenum
 lda renumbank        ;renum tool: RENUM_BANK $8000
launchtool
 pha
 lda #$80
 sta CPSRC
 lda #$c0
 sta CPDST
 pla
 ldx #12              ;12 pages = 3K (must match PAGER_MAX in tools/make_crt.py)
 jsr copyrun          ;copy the tool to $c000 and run it; it RTSs back here
fin
 lda SAV01
 sta R6510
 jmp NMIRTI           ;finish the NMI -> RTI resumes the editor with its screen intact

;copyrun: A = cart bank, X = page count, CPSRC/CPDST = source/dest page hi.
;Pages the bank in, copies X*256 bytes from CPSRC:00 to CPDST:00, pages the cart
;out, and JMPs CPDST:00. The copied code RTSs back to copyrun's caller.
copyrun
 sta CART             ;page in the bank
 stx CPPAGES
 ldy #0
 sty SRCZP
 sty DSTZP
 lda CPSRC
 sta SRCZP+1
 lda CPDST
 sta DSTZP+1
 sta jt+2             ;self-modify the JMP hi byte -> CPDST:00
crl
 lda (SRCZP),y
 sta (DSTZP),y
 iny
 bne crl
 inc SRCZP+1
 inc DSTZP+1
 dec CPPAGES
 bne crl
 lda #$80
 sta CART             ;page the cart out
jt
 jmp $0000            ;hi byte self-modded to CPDST -> run the copied code
