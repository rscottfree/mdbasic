; ***MDBASIC packaged-program boot stub***
; Embedded in every PRG written by the PACKAGE tool (pack_tool.asm). The
; packaged file loads at $0302 with LOAD"NAME",8,1: the first word lands on
; the IMAIN vector ($0302) and points it here, the next 48 bytes rewrite
; $0304-$0333 with their standard KERNAL/BASIC values (harmless -- they are
; overwritten mid-load with the bytes they already hold, so no torn vector is
; ever observable), and this stub lands in the cassette buffer at $0334. The
; BASIC program body loads at its final home $0801 and the 16K MDBASIC image
; loads right after it (progend..progend+$3fff, under the BASIC ROM when the
; program is large -- writes always fall through to RAM).
;
; When the direct-mode LOAD finishes, BASIC relinks the program (its own
; end-of-program marker stops the walk before the appended image), prints
; READY and jumps through IMAIN -> here. The stub then:
;   1. restores IMAIN to the standard $a483,
;   2. copies the image to $8000-$bfff (strictly descending byte copy: the
;      destination is always >= the source, so top-down never overwrites
;      unread source bytes, whatever the program size),
;   3. points TXTTAB/VARTAB at the packaged program,
;   4. installs MDBASIC exactly as its reset path does -- newvec + initclk
;      with the BASIC ROM paged out (resvec's own sequence, minus the KERNAL
;      re-init that a freshly booted machine has already done, and minus the
;      banner) -- so the machine ends up in the same state as "LOAD MDBASIC,
;      SYS 64738",
;   5. types RUN for the user: initmdb (inside newvec) just cleared the
;      keyboard queue, so stuff RUN+RETURN into it afterwards and enter the
;      main BASIC loop -- the same path a hand-typed RUN takes, IGONE hooks
;      and all.
;
; NEWVEC/INITCLK below are sentinels: the build patches the two jsr operands
; with the real addresses read from mdbasic.lst (see tools/pack_prg.py). The
; progend word is patched per-package by the PACKAGE tool with the program's
; VARTAB, which is both the byte after the program and the file position where
; the image section loaded.
;
; Assembled at $0334; must stay <= 204 bytes ($0334-$03ff).

R6510   = $01
TXTTAB  = $2b
VARTAB  = $2d
SRC     = $fb         ;copy pointers -- free zp on a machine sitting at READY
DST     = $fd
NDX     = $c6         ;number of chars in the keyboard queue
KEYD    = $0277       ;the keyboard queue
IMAIN   = $0302       ;BASIC main-loop vector (standard value $a483)
CLRSCR  = $e544       ;kernal clear screen
MAINLP  = $e39d       ;reset stack then enter the main BASIC loop (READY)
NEWVEC  = $caf1       ;sentinel -> mdbasic newvec  (patched at build time)
INITCLK = $caf2       ;sentinel -> mdbasic initclk (patched at build time)

*=$0334

 jmp begin
progend .word $ffff   ;patched per-package: VARTAB = program end = image start

begin
 sei
 lda #$83             ;put the standard main-loop vector back
 sta IMAIN
 lda #$a4
 sta IMAIN+1
;copy the 16K image from progend (where the file loaded it) to $8000-$bfff.
;dst-src = $8000-progend >= 0 always, so a strictly descending byte copy can
;never overwrite a source byte it has not read yet (degenerates to a harmless
;in-place copy for a maximal 30K program). Writes to $a000-$bfff fall through
;to the RAM under the BASIC ROM.
 lda progend
 sta SRC
 lda progend+1
 clc
 adc #$3f
 sta SRC+1            ;src page ptr = progend+$3f00; (SRC),y=$ff is the top byte
 lda #$00
 sta DST
 lda #$bf
 sta DST+1
 ldx #$40             ;64 pages
cpage
 ldy #$ff
cbyte
 lda (SRC),y
 sta (DST),y
 dey
 cpy #$ff             ;y wrapped: whole page done ($ff down to $00)
 bne cbyte
 dec SRC+1
 dec DST+1
 dex
 bne cpage
;point BASIC at the packaged program (the LOAD left VARTAB at the file end)
 lda #$01
 sta TXTTAB
 lda #$08
 sta TXTTAB+1
 lda progend
 sta VARTAB
 lda progend+1
 sta VARTAB+1
;install MDBASIC the way resvec does: newvec + initclk with BASIC ROM out
 lda R6510
 and #%11111110
 sta R6510
 jsr NEWVEC           ;MDBASIC vector overrides + initmdb + MEMSIZ=$7fff
 jsr INITCLK          ;init TOD clocks
 inc R6510
 cli
 jsr CLRSCR           ;drop the load-time screen contents
;auto-type RUN (after newvec: initmdb cleared the keyboard queue)
 ldx #3
stuff
 lda runtxt,x
 sta KEYD,x
 dex
 bpl stuff
 lda #4
 sta NDX
 jmp MAINLP
runtxt .text "run"
 .byte $0d
