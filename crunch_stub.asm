; ***MDBASIC crunched-package self-extraction stub***
; Embedded in every CRUNCHED PRG written by the PACKAGE tool (pack_tool.asm,
; crunch option) -- the compressed sibling of pack_stub.asm. The crunched file
; loads at $0302 with LOAD"NAME",8,1: the first word points IMAIN here, the
; next 48 bytes rewrite $0304-$0333 with their standard values (same mid-load
; safety argument as pack_stub.asm), $0400-$05ff show a banner while loading,
; this stub loads at $0600, an empty program ($00,$00 at $0801) keeps BASIC's
; load-time relink off the payload, and the compressed payload loads at $0803.
;
; When the direct-mode LOAD finishes, BASIC relinks the (empty) program,
; prints READY and jumps through IMAIN -> here. The stub then:
;   1. restores IMAIN and banks everything out ($01=$34: the payload gets
;      relocated under the KERNAL and the image is written under BASIC ROM),
;   2. plants RAM NMI/IRQ vectors at $fffa-$ffff (an RTI stub -- a RESTORE
;      press during decrunch must not vector through payload bytes),
;   3. relocates the payload so its last byte sits at $fff9, reading the end
;      address from the KERNAL load-end pointer $ae/$af (no length patching:
;      the stub is fully constant). The descending copy is safe because the
;      destination is always above the source,
;   4. decodes the two chunks (program -> $0801, image -> $8000) with the
;      lz_decrunch algorithm of tools/pack_prg.py -- see the format comment
;      there; the forward decode cannot catch the relocated payload, which
;      tools/pack_prg.py proves per file (_assert_decrunch_safe). VARTAB is
;      the write cursor after the first (program) chunk,
;   5. installs MDBASIC and auto-types RUN exactly as pack_stub.asm does
;      (newvec + initclk sentinels patched at build time, keyboard queue).
;
; Assembled at $0600; must stay <= 512 bytes ($0600-$07ff).

R6510   = $01
CNT     = $22         ;chunk output down-counter (2)
BITB    = $24         ;control-bit reservoir (asl empties it, $00 = refill)
OFFL    = $25         ;match offset-1 low
OFFH    = $26         ;match offset-1 high
LENV    = $27         ;gamma value, then the match copy counter
SRC     = $28         ;match copy source (2)
TXTTAB  = $2b
VARTAB  = $2d
EAL     = $ae         ;KERNAL load end pointer = one past the payload
NDX     = $c6         ;number of chars in the keyboard queue
RD      = $fb         ;payload read cursor (2)
WR      = $fd         ;output write cursor (2)
KEYD    = $0277       ;the keyboard queue
IMAIN   = $0302       ;BASIC main-loop vector (standard value $a483)
PAYLOAD = $0803       ;payload home in the file (after the $0801 decoy)
RELTOP  = $fffa       ;one past the relocated payload's last byte ($fff9)
MAINLP  = $e39d       ;reset stack then enter the main BASIC loop (READY)
NEWVEC  = $caf1       ;sentinel -> mdbasic newvec  (patched at build time)
INITCLK = $caf2       ;sentinel -> mdbasic initclk (patched at build time)

*=$0600

 sei
 lda #$83             ;put the standard main-loop vector back
 sta IMAIN
 lda #$a4
 sta IMAIN+1
 lda #$34
 sta R6510            ;all RAM: payload under the KERNAL, image under BASIC
 lda #<nmirti         ;plant RAM NMI/IRQ vectors above the relocated payload
 sta $fffa
 sta $fffe
 lda #>nmirti
 sta $fffb
 sta $ffff
;relocate the payload $0803..EAL-1 so its last byte lands at $fff9: descending
;copy, dst >= src always (the payload never reaches $8000, see FILE_END_MAX
;and the slack check in tools/pack_prg.py)
 lda EAL
 sta RD
 lda EAL+1
 sta RD+1
 lda #<RELTOP
 sta WR
 lda #>RELTOP
 sta WR+1
reloc
 lda RD
 bne rel1
 dec RD+1
rel1
 dec RD
 lda WR
 bne rel2
 dec WR+1
rel2
 dec WR
 ldy #0
 lda (RD),y
 sta (WR),y
 lda RD
 cmp #<PAYLOAD
 bne reloc
 lda RD+1
 cmp #>PAYLOAD
 bne reloc
;decode: read cursor = relocated payload start
 lda WR
 sta RD
 lda WR+1
 sta RD+1
 jsr dchunk           ;chunk 1: the program -> $0801
 lda WR               ;write cursor = program end = VARTAB
 sta VARTAB
 lda WR+1
 sta VARTAB+1
more
 jsr dchunk           ;chunk 2: the image -> $8000; then the terminator
 bcc more
;install MDBASIC the way resvec does: newvec + initclk with BASIC ROM out
;(same sequence as pack_stub.asm)
 lda #$01
 sta TXTTAB
 lda #$08
 sta TXTTAB+1
 lda #$36
 sta R6510            ;KERNAL+I/O in, BASIC ROM out
 jsr NEWVEC           ;MDBASIC vector overrides + initmdb + MEMSIZ=$7fff
 jsr INITCLK          ;init TOD clocks
 inc R6510
 cli
;auto-type {clr}RUN (after newvec: initmdb cleared the keyboard queue).
;Unlike pack_stub.asm this stub must NOT jsr CLRSCR: it runs inside screen
;RAM, so a direct clear would wipe its own code. The queued $93 makes the
;main loop do the clearing after this code has finished.
 ldx #4
stuff
 lda runtxt,x
 sta KEYD,x
 dex
 bpl stuff
 lda #5
 sta NDX
 jmp MAINLP

;==================== one chunk ====================
;dest u16, outlen u16, then the item stream; C=1 = terminator (dest $0000)
dchunk
 jsr rdbyte
 sta WR
 jsr rdbyte
 sta WR+1
 ora WR
 bne dc1
 sec                  ;dest $0000: payload done
 rts
dc1
 jsr rdbyte
 sta CNT
 jsr rdbyte
 sta CNT+1
 lda #0
 sta BITB             ;reservoir starts empty per chunk
item
 lda CNT
 ora CNT+1
 beq dcdone
 jsr getbit
 bcc match
;literal: one whole byte
 jsr rdbyte
 ldy #0
 sta (WR),y
 jsr incwr
 jsr deccnt
 jmp item
;match: offset-type bit, [4 high bits], low byte, gamma(length-1)
match
 lda #0
 sta OFFH
 jsr getbit
 bcc shortoff
 ldx #4
offhi
 jsr getbit
 rol OFFH
 dex
 bne offhi
shortoff
 jsr rdbyte
 sta OFFL
;gamma, MSB-first: count zeros, then that many value bits after the lead 1
 ldx #0
gzero
 jsr getbit
 bcs gval
 inx
 bne gzero            ;always (x <= 7 for lengths <= 255)
gval
 lda #1
 sta LENV
gbits
 cpx #0
 beq gdone
 jsr getbit
 rol LENV
 dex
 jmp gbits
gdone
;copy length = LENV+1 bytes from WR-(OFFH:OFFL)-1
 lda WR
 sec
 sbc OFFL
 sta SRC
 lda WR+1
 sbc OFFH
 sta SRC+1
 lda SRC
 bne src1
 dec SRC+1
src1
 dec SRC
 inc LENV
copy
 ldy #0
 lda (SRC),y
 sta (WR),y
 inc SRC
 bne cp1
 inc SRC+1
cp1
 jsr incwr
 jsr deccnt
 dec LENV
 bne copy
 jmp item
dcdone
 clc
 rts

;==================== helpers ====================
rdbyte
 ldy #0
 lda (RD),y
 inc RD
 bne rb1
 inc RD+1
rb1
 rts

;next control bit -> carry (reservoir byte fetched inline when empty; the
;bit-0 guard set on refill marks how many real bits remain)
getbit
 asl BITB
 beq gbref
 rts
gbref
 jsr rdbyte
 sec
 rol a
 sta BITB
 rts

incwr
 inc WR
 bne iw1
 inc WR+1
iw1
 rts

deccnt
 lda CNT
 bne dcn1
 dec CNT+1
dcn1
 dec CNT
 rts

nmirti
 rti

runtxt .byte $93      ;{clr}
 .text "run"
 .byte $0d
