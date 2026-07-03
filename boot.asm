; ***MDBASIC Magic Desk boot loader (with docs-pager install)***
;
; Reconstruction of the original cart_boot.bin (cold start + a position-
; independent copier that streams the 16K image from the banked $8000-$9fff
; window into RAM) plus a docs-pager install step. After copying the image, and
; before disabling the cart, the copier:
;   A. copies the HELP handler from cart bank 3 ($9800) to $033c (cassette buffer)
;   B. disables the cart, then stashes the image's original `execut` address
;      (read through the patched `troffptr`) at REALGONE and patches the two
;      `troff` operand bytes so IGONE points at the $033c handler.
; In a plain (non-docs) cart `troffptr` is left $0000 and the install is skipped.
;
; tools/make_crt.py patches `troffptr` with the image address of troff's ldx
; operand (troff+1), read from mdbasic.lst.

HANDLER_SRC = $9800     ;handler location in cart bank 3 (bank offset $1800)
HANDLER_DST = $033c     ;cassette buffer (unused by MDBASIC)
HANDLER_LEN = $80       ;128 bytes copied (handler is ~120)
REALGONE    = $03f8     ;stash for the original execut address (lo,hi)
HELP_BANK   = 3
TRPTR       = $5c       ;zp pointer to troff's ldx operand (set by cold start)

*=$8000

 .word cold, cold       ;cold + warm cart vectors
 .byte $c3,$c2,$cd,$38,$30   ;"CBM80" autostart signature
docsflag
 .word $0000            ;make_crt sets nonzero to enable the docs-pager install

cold
 sei
 cld
 ldx #$fb
 txs
 jsr $fda3              ;IOINIT
 jsr $fd50              ;RAMTAS
 lda #$a0
 sta $0284              ;MEMSIZ hi = $a000
 jsr $fd15              ;RESTOR (KERNAL vectors)
 jsr $ff5b              ;CINT (screen/VIC)
 cli
 lda $d011
 and #$ef
 sta $d011              ;blank screen during copy
 ;remember the docs flag for the copier (read here while bank 0 stub is visible)
 lda docsflag
 sta TRPTR
 lda docsflag+1
 sta TRPTR+1
 ;set up the image copy: bank 0, count $4000, dest $8000, src = payload
 lda #0
 sta $57                ;current bank
 lda #$00
 sta $58                ;count lo
 lda #$40
 sta $59                ;count hi
 lda #$00
 sta $2d                ;dest lo
 lda #$80
 sta $2e                ;dest hi ($8000)
 lda #<payload
 sta $5a                ;src lo
 lda #>payload
 sta $5b                ;src hi
 ;copy the position-independent copier to $0400 and run it
 ldx #0
cpc
 lda copier,x
 sta $0400,x
 inx
 bne cpc
 jmp $0400

;--- position-independent copier (executes from $0400) ---
copier
 ldx #0
 lda $57
 sta $de00              ;select current bank
cloop
 lda ($5a,x)
 sta ($2d,x)
 inc $5a
 bne cnext
 inc $5b
 lda $5b
 cmp #$a0               ;src crossed $a000 -> advance bank
 bne cnext
 lda #$80
 sta $5b
 inc $57
 lda $57
 sta $de00
cnext
 inc $2d
 bne cdec
 inc $2e
cdec
 dec $58
 bne cloop
 dec $59
 lda $59
 cmp #$ff
 bne cloop
 ;--- docs-pager install (skipped if docsflag is $0000) ---
 lda TRPTR
 ora TRPTR+1
 beq finish             ;no docs -> just disable + reset
 ;A. copy the RESTORE handler from bank 3 to $033c (cart still on)
 lda #HELP_BANK
 sta $de00
 ldx #0
hc
 lda HANDLER_SRC,x
 sta HANDLER_DST,x
 inx
 cpx #HANDLER_LEN
 bne hc
 ;B. cart off, then stash the original runstp ($8002) and repoint the image's
 ;   cart NMI vector at the $033c handler so CTRL+RESTORE opens the docs pager.
 lda #$80
 sta $de00              ;cart OFF -> $8000-$9fff is the RAM image
 lda $8002              ;original runstp (RESTORE/NMI vector) lo
 sta REALGONE
 lda $8003
 sta REALGONE+1
 lda #<HANDLER_DST
 sta $8002              ;repoint cart NMI vector -> $033c
 lda #>HANDLER_DST
 sta $8003
 ;Enter the image's resvec just past its `jsr RAMTAS` (resvec+14) so the
 ;handler we just put in $033c is not wiped by a second RAMTAS. The loader's
 ;cold start already did IOINIT/RAMTAS; resvec+14 picks up at RESTOR.
 lda $8000              ;image reset vector (resvec) lo
 clc
 adc #14
 sta TRPTR
 lda $8001              ;resvec hi
 adc #0
 sta TRPTR+1
 cli
 jmp (TRPTR)
finish
 lda #$80
 sta $de00              ;disable cart
 cli
 jmp ($fffc)

payload
 ;the 16K MDBASIC image is appended here by make_crt.py
