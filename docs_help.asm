; ***MDBASIC docs-pager RESTORE handler***
; Freeze-cartridge style trigger: pressing CTRL+RESTORE opens the docs pager.
;
; The boot loader copies this code from a cart bank to $033c (cassette buffer),
; stashes the image's original runstp (RESTORE/NMI) address at REALGONE, and
; patches the image's cart NMI vector ($8002) to point here. The KERNAL cart-NMI
; path then jumps ($8002) -> here on every RESTORE. This code is reached ONLY on
; a RESTORE press -- never on the normal execution path -- so it cannot disturb
; running programs.
;
;   CTRL + RESTORE       -> always open the docs pager (from the start; search
;                           inside). Editor modes are cleared so we return clean.
;   RESTORE alone        -> the original runstp behaviour: reset editor modes
;                           (Quote/Insert/Reverse), or a no-op if none are active.
;   RUN/STOP + RESTORE   -> the original runstp behaviour (break), via REALGONE.
;
; CTRL is detected for free: SCNSTOP scans keyboard-matrix row 7 into STKEY ($91)
; for the STOP test, and CTRL shares that row (STOP = bit 7, CTRL = bit 2; 0 =
; pressed). So no IRQ keyscan / SHFLAG dependence -- works even with IRQs masked.
;
; Assembled for $033c (its install/run address). See docs-pager design.

R6510    = $01
CART     = $de00
QTSW     = $d4        ;editor quote-mode flag
RVS      = $c7        ;editor reverse flag
INSRT    = $d8        ;editor insert count
STKEY    = $91        ;keyboard-matrix row 7 (STOP=bit7, CTRL=bit2), set by SCNSTOP
STOP     = $ffe1      ;kernal: test the STOP key (Z=1 if pressed)
SCNSTOP  = $f6bc      ;kernal: scan keyboard, STOP result in $91
NMIRTI   = $fe72      ;kernal NMI tail: pops A/X/Y and RTIs to the interrupted
                      ;code (same return runstp uses for plain RESTORE) -- so the
                      ;editor resumes with no fresh READY printed
INDEX_BANK = 3
SRCZP    = $fb
DSTZP    = $fd
REALGONE = $03f8      ;original runstp address (lo,hi), stashed by the loader

*=$033c

boot
 jsr SCNSTOP          ;scan keyboard for STOP
 jsr STOP             ;STOP key pressed too?
 beq tonormal         ;RUN/STOP+RESTORE -> original runstp (break)
 ;CTRL held? SCNSTOP already latched row 7 into STKEY; bit 2 = 0 means pressed.
 lda STKEY
 and #$04
 beq dodocs           ;CTRL+RESTORE -> always open the docs pager
tonormal
 jmp (REALGONE)       ;plain RESTORE -> original runstp (editor-mode reset / no-op)

dodocs
 ;CTRL+RESTORE always opens docs (the pager itself always opens at the first
 ;topic). Clear any active editor mode first so the resumed editor isn't left
 ;stuck in a prior Quote/Insert/Rvs mode on exit.
 lda #0
 sta QTSW             ;editor quote-mode flag
 sta INSRT            ;editor insert count
 sta RVS              ;editor reverse flag
 sta SRCZP            ;lo bytes of src/dst pointers
 sta DSTZP
 tay                  ;Y = 0 for the copy loop
 sei
 lda #$37
 sta R6510            ;BASIC+KERNAL+I/O in, cart visible at $8000
 lda #INDEX_BANK
 sta CART             ;page in the pager bank
 lda #$80
 sta SRCZP+1          ;src = $8000
 lda #$c0
 sta DSTZP+1          ;dst = $c000
 ldx #12              ;12 pages = 3K (must match PAGER_MAX in tools/make_crt.py)
copy
 lda (SRCZP),y
 sta (DSTZP),y
 iny
 bne copy
 inc SRCZP+1
 inc DSTZP+1
 dex
 bne copy
 lda #$80
 sta CART             ;page the cart out
 jsr $c000            ;run the pager (restores screen/cursor/colors; CLIs on exit)
 jmp NMIRTI           ;finish the NMI normally -> RTI resumes the interrupted
                      ;editor with its screen intact (no fresh READY)
