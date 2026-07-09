; ***MDBASIC CTRL+RESTORE utility menu -- $033c stub***
; Freeze-cartridge style trigger: pressing CTRL+RESTORE shows a tiny function-key
; menu that launches the docs pager (F1) or the renumber/move/copy tools (R/M/C).
;
; The boot loader copies this stub from cart bank 3 ($9800) to $033c (cassette
; buffer), stashes the image's original runstp (RESTORE/NMI) address at REALGONE,
; and patches the image's cart NMI vector ($8002) to point here. The KERNAL
; cart-NMI path then jumps ($8002) -> here on every RESTORE. This code is reached
; ONLY on a RESTORE press -- never on the normal execution path -- so it cannot
; disturb running programs.
;
;   CTRL + RESTORE       -> show the utility menu (F1 docs, R renumber,
;                           M move, C copy,
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
; (RENUM_BANK $9800, drawn at $c000, returns the choice), then to copy+run the
; chosen tool (also at $c000, over the now-defunct menu-body). Each tool RTSs back
; here and this stub does the single NMI-tail RTI. See renum-move-tool-plan.
;
; menu_body.asm is the ONLY place that snapshots screen RAM + cursor + blink
; state (into SCRBUF + the SAVD3/SAVD6/SAVPNT/SAVHIB/SAVBLN zero-page handoff) --
; the docs pager and edit tools no longer duplicate that save; they only restore
; from the same handoff at their own exit. `runmenu` always runs menu_body before
; any tool, in one of two modes selected by SAVEONLY: the real CTRL+RESTORE path
; (domenu) wants the full F1/R/M/C/STOP UI; the direct test-bypass entries
; (which skip the UI) still need the save to happen, so they set SAVEONLY=1 and
; menu_body just snapshots and returns immediately.
;
; make_crt.py patches `toolbanks` (fixed offsets 3..5, right after the opening
; JMP) with the actual R/M/C tool bank numbers, which vary with doc-data count.

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
SAVEONLY = $0e        ;shared flag read by menu_body.asm's `start`: 0 = show the
                      ;full F1/R/M/C/STOP UI (domenu); nonzero = skip the UI and
                      ;just save screen/cursor/blink state, then return (dodocs/
                      ;dorenum). Also safe during this NMI -- see SRCZP above.
CHOICE   = $0f        ;direct-entry choice for tests (1 docs, 2 R, 3 M, 4 C)

*=$033c

 jmp start
toolbanks .byte $ff,$ff,$ff ;offsets 3..5: RENUM/MOVE/COPY banks, patched by make_crt.py

start
 jsr SCNSTOP          ;scan keyboard for STOP
 jsr STOP             ;STOP key pressed too?
 beq tonormal         ;RUN/STOP+RESTORE -> original runstp (break)
 lda STKEY            ;CTRL held? bit 2 = 0 means pressed
 and #$04
 beq domenu           ;CTRL+RESTORE -> show the menu
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
 lda R6510
 sta SAV01
 lda #$37
 sta R6510
 lda #1
 sta SAVEONLY
 jsr runmenu
 ldx CHOICE
 jmp dispatch

domenu
 lda R6510
 sta SAV01
 lda #$37
 sta R6510            ;BASIC+KERNAL+I/O in, cart visible at $8000
 lda #0
 sta SAVEONLY         ;full F1/R/M/C/STOP UI this time (not the quick save-only path)
 jsr runmenu          ;X = choice (0/1/2)
dispatch
 cpx #1
 beq lpager
 cpx #2
 bcc fin              ;0 = dismissed, launch nothing
 txa
 sec
 sbc #2
 tax
 lda toolbanks,x      ;2/3/4 -> renumber/move/copy bank
 ldx #12              ;12 pages = 3K, leaves SCRBUF at $cc00 intact
 bne launchtool
lpager
 lda #INDEX_BANK      ;docs pager: bank 3 $8000
 ldx #12              ;12 pages = 3K (must match PAGER_MAX in tools/make_crt.py)
launchtool
 pha
 lda #$80
 sta CPSRC
 lda #$c0
 sta CPDST
 pla
 jsr copyrun          ;copy the tool to $c000 and run it; it RTSs back here
fin
 lda SAV01
 sta R6510
 jmp NMIRTI           ;finish the NMI -> RTI resumes the editor with its screen intact

;runmenu: copy the first tool bank's menu-body to $c000 and run it (per SAVEONLY,
;either the full UI, returning the F1/R/M/C/STOP choice in X, or the quick save-only path,
;whose X is undefined -- callers that set SAVEONLY=1 ignore it).
runmenu
 lda #$98             ;menu-body sits at first tool bank $9800 (MENU_OFF in make_crt.py)
 sta CPSRC
 lda #$c0
 sta CPDST
 lda toolbanks
 ldx #2               ;2 pages is ample for the menu-body UI
 jmp copyrun          ;copyrun's JMP-in / RTS-out makes this a tail call

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
