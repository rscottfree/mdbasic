; ***MDBASIC CTRL+RESTORE launcher***
; Copied by menu.asm from the first tool bank's $9a00 to $0200, so it can stay
; resident outside $c000 while it:
;   1. copies menu_body.asm to $c000 and runs it;
;   2. copies the chosen pager/tool to $c000 and jumps into it;
;   3. on menu dismiss only, restores $01 and finishes through the KERNAL NMI
;      tail. The pager/tools restore $01 themselves from SAV01 and tail out.

R6510    = $01
CART     = $de00
NMIRTI   = $fe72
INDEX_BANK = 3
FIRSTBANK = $033f
CPPAGES  = $02
SAV01    = $05
SAVEONLY = $0e
CHOICE   = $0f
SRCZP    = $fb
DSTZP    = $fd

*=$0200

start
 lda FIRSTBANK
 ldx #2
 ldy #$98
 jsr copyrun          ;menu-body -> $c000, then RTS with X = choice (or undefined)
 lda SAVEONLY
 beq dispatch
 ldx CHOICE
dispatch
 cpx #0
 beq dismiss
 cpx #1
 beq lpager
 txa
 sec
 sbc #2
 clc
 adc FIRSTBANK        ;2/3/4 -> renumber/move/copy bank
 ldx #12
 ldy #$80
 bne launchtool
lpager
 lda #INDEX_BANK      ;docs pager is fixed at bank 3 $8000
 ldx #12
 ldy #$80
launchtool
 jmp jumprun          ;tool/pager -> $c000, owns the NMI tail from here

dismiss
 lda SAV01
 sta R6510
 jmp NMIRTI

copyrun
 jsr copybody
 jsr $c000
 rts

jumprun
 jsr copybody
 jmp $c000

copybody
 sta CART
 stx CPPAGES
 sty SRCZP+1
 lda #0
 sta SRCZP
 sta DSTZP
 lda #$c0
 sta DSTZP+1
 ldy #0
cp_loop
 lda (SRCZP),y
 sta (DSTZP),y
 iny
 bne cp_loop
 inc SRCZP+1
 inc DSTZP+1
 dec CPPAGES
 bne cp_loop
 lda #$80
 sta CART
 rts
