; ***MDBASIC number-base convert tool***
; A full-screen REPL launched from the CTRL+RESTORE menu. Copied to $c000
; from its own tool bank and jumped to by the resident stub; RUN/STOP restores
; state, RTSs back to menu.asm, and that shared stub does the single KERNAL
; NMI tail.
;
; Input is one number per prompt:
;   %...   binary
;   @...   octal
;   $...   hexadecimal
;   ...    decimal
;
; On RETURN, the tool prints the other three representations (one per line)
; and then shows another prompt. Invalid / overflowing input prints ?INVALID.
; Assembled for $c000 (run location).

R6510    = $01
BLNSW    = $cc        ;cursor blink enable ($00=blinks, nonzero=disabled)
GDCHAR   = $ce
BLNON    = $cf
BLNCT    = $cd        ;cursor blink countdown (20 = one full period)
PNT      = $d1        ;pointer to the current screen line (lo/hi)
PNTR     = $d3        ;cursor column on the current line
TBLX     = $d6        ;cursor physical row
HIBASE   = $0288
NMIVEC   = $0318
SCREEN   = $0400
SCRBUF   = $cc00
SCROLY   = $d011
VMCSB    = $d018
CI2PRA   = $dd00
CLRSCR   = $e544
CHROUT   = $ffd2
GETIN    = $ffe4
STRP     = $26

;--- shared CTRL+RESTORE-menu screen/cursor/blink handoff (see menu_body.asm) ---
SAV01    = $05        ;resident stub's saved original $01
SAVD3    = $06        ;saved PNTR (cursor column)
SAVD6    = $07        ;saved TBLX (cursor row)
SAVPNT   = $08        ;saved PNT lo($08)/hi($09)
SAVHIB   = $0a        ;saved HIBASE (screen page at CTRL+RESTORE time)
SAVBLN   = $0d        ;saved BLNSW (blink-enable state at CTRL+RESTORE time)

BASE_BIN = 0
BASE_OCT = 1
BASE_HEX = 2
BASE_DEC = 3

*=$c000

;==================== entry ====================
start
 lda R6510
 sta sav01
 lda #$37
 sta R6510            ;BASIC+KERNAL+I/O in
 lda #1
 sta BLNSW            ;disable cursor blink for the session
 lda NMIVEC
 sta savnmi
 lda NMIVEC+1
 sta savnmi+1
 lda #<nmistub
 sta NMIVEC
 lda #>nmistub
 sta NMIVEC+1
 lda SAVD3
 sta svd3
 lda SAVD6
 sta svd6
 lda SAVPNT
 sta svpnt
 lda SAVPNT+1
 sta svpnt+1
 lda SAVHIB
 sta svhib
 lda SAVBLN
 sta svbln
 jsr forcetext
 jsr CLRSCR
 lda #<hdrtxt
 ldy #>hdrtxt
 jsr prstrAY

;==================== REPL ====================
repl
 lda #">"
 jsr CHROUT
 jsr readline
 bcs texit            ;RUN/STOP -> leave
 jsr doconvert
 jmp repl

;==================== exit ====================
texit
 lda savnmi
 sta NMIVEC
 lda savnmi+1
 sta NMIVEC+1
 lda svhib
 cmp #$04
 bne tblank
 jsr forcetext
 jsr restorescreen
 lda svbln
 sta BLNSW
 lda #$ff
 sta BLNON
 lda #1
 sta BLNCT
 lda SAV01
 sta R6510
 rts
tblank
 jsr forcetext
 sei
 jsr CLRSCR
 lda #$20
 sta GDCHAR
 lda svbln
 sta BLNSW
 lda #$ff
 sta BLNON
 lda SAV01
 sta R6510
 rts

nmistub
 rti

;force canonical text screen
forcetext
 lda CI2PRA
 ora #%00000011       ;VIC 16K bank 0
 sta CI2PRA
 lda #%00011011       ;bitmap/ext-color off, 25 rows, display on
 sta SCROLY
 lda #%00010101       ;video matrix $0400 + uppercase charset
 sta VMCSB
 lda #$04
 sta HIBASE
 rts

;==================== screen restore ====================
restorescreen
 ldx #0
rs_cp
 lda SCRBUF,x
 sta SCREEN,x
 lda SCRBUF+$100,x
 sta SCREEN+$100,x
 lda SCRBUF+$200,x
 sta SCREEN+$200,x
 lda SCRBUF+$300,x
 sta SCREEN+$300,x
 inx
 bne rs_cp
 lda svd3
 sta PNTR
 lda svd6
 sta TBLX
 lda svpnt
 sta PNT
 lda svpnt+1
 sta PNT+1
 rts

;==================== line input ====================
readline
 lda #0
 sta bufi
 jsr showcursor
rl_lp
 jsr GETIN
 beq rl_lp
 cmp #$0d             ;RETURN
 beq rl_done
 cmp #$03             ;RUN/STOP
 beq rl_stop
 cmp #$14             ;DEL
 beq rl_del
 cmp #$20             ;ignore other control codes ($00-$1f)
 bcc rl_lp
 cmp #$80             ;$20-$7f are printable -- take them
 bcc rl_ok
 cmp #$a0
 bcc rl_lp            ;$80-$9f: shifted control codes (cursor/color/f-keys)
rl_ok
 ldx bufi
 cpx #38
 bcs rl_lp
 pha
 jsr hidecursor
 pla
 sta inbuf,x
 jsr CHROUT
 inc bufi
 jsr showcursor
 jmp rl_lp
rl_del
 lda bufi
 beq rl_lp
 jsr hidecursor
 dec bufi
 lda #$14
 jsr CHROUT
 jsr showcursor
 jmp rl_lp
rl_done
 jsr hidecursor
 lda #$0d
 jsr CHROUT
 ldx bufi
 lda #0
 sta inbuf,x
 clc
 rts
rl_stop
 sec
 rts

showcursor
 ldy PNTR
 lda #$a0
 sta (PNT),y
 rts

hidecursor
 ldy PNTR
 lda #$20
 sta (PNT),y
 rts

;==================== convert ====================
doconvert
 jsr lineblank
 bcc dc_parse
 rts
dc_parse
 jsr parse_value
 bcs dc_ok
 lda #<serr
 ldy #>serr
 jsr prstrAY
 lda #$0d
 jsr CHROUT
 jmp print_blank_line
dc_ok
 lda inbase
 cmp #BASE_DEC
 beq dc_skip_dec
 jsr print_dec
dc_skip_dec
 lda inbase
 cmp #BASE_BIN
 beq dc_skip_bin
 jsr print_bin
dc_skip_bin
 lda inbase
 cmp #BASE_HEX
 beq dc_skip_hex
 jsr print_hex
dc_skip_hex
 lda inbase
 cmp #BASE_OCT
 beq dc_skip_oct
 jsr print_oct
dc_skip_oct
 jmp print_blank_line

lineblank
 ldx #0
lb_lp
 lda inbuf,x
 beq lb_yes
 cmp #$20
 bne lb_no
 inx
 bne lb_lp
lb_yes
 sec
 rts
lb_no
 clc
 rts

parse_value
 lda #0
 sta value32
 sta value32+1
 sta value32+2
 sta value32+3
 sta negflag
 sta sawdig
 ldx #0
 jsr skipspaces
 lda inbuf,x
 cmp #"+"
 beq pv_plus
 cmp #"-"
 bne pv_prefix
 lda #1
 sta negflag
 inx
 jsr skipspaces
 jmp pv_prefix
pv_plus
 inx
 jsr skipspaces
pv_prefix
 lda #BASE_DEC
 sta inbase
 lda inbuf,x
 cmp #"%"
 bne pv_ck_oct
 lda #BASE_BIN
 sta inbase
 inx
 jmp pv_loop
pv_ck_oct
 cmp #"@"
 bne pv_ck_hex
 lda #BASE_OCT
 sta inbase
 inx
 jmp pv_loop
pv_ck_hex
 cmp #"$"
 bne pv_loop
 lda #BASE_HEX
 sta inbase
 inx
pv_loop
 lda inbuf,x
 beq pv_end
 cmp #$20
 beq pv_sp
 jsr getdigit
 bcs pv_gotdig
 jmp pv_bad
pv_gotdig
 sta digitv
 inc sawdig
 lda inbase
 cmp #BASE_DEC
 beq pv_dec
 cmp #BASE_BIN
 beq pv_bin
 cmp #BASE_OCT
 beq pv_oct
 jsr shl_value
 bcs pv_bad
 jsr shl_value
 bcs pv_bad
 jsr shl_value
 bcs pv_bad
 jsr shl_value
 bcs pv_bad
 lda digitv
 jsr add_digit_value
 bcs pv_bad
 jmp pv_next
pv_bin
 jsr shl_value
 bcs pv_bad
 lda digitv
 jsr add_digit_value
 bcs pv_bad
 jmp pv_next
pv_oct
 jsr shl_value
 bcs pv_bad
 jsr shl_value
 bcs pv_bad
 jsr shl_value
 bcs pv_bad
 lda digitv
 jsr add_digit_value
 bcs pv_bad
 jmp pv_next
pv_dec
 jsr mul10_value
 bcs pv_bad
 lda digitv
 jsr add_digit_value
 bcs pv_bad
pv_next
 inx
 jmp pv_loop
pv_sp
 inx
 jmp pv_loop
pv_end
 lda sawdig
 bne pv_have
pv_bad
 clc
 rts
pv_have
 lda negflag
 beq pv_pos
 jsr value_gt_maxneg
 bcs pv_bad
 jsr negate_value
 sec
 rts
pv_pos
 lda inbase
 cmp #BASE_DEC
 bne pv_ok
 jsr value_gt_maxpos
 bcs pv_bad
pv_ok
 sec
 rts

skipspaces
 lda inbuf,x
 cmp #$20
 bne ss_x
 inx
 bne skipspaces
ss_x
 rts

getdigit
 cmp #"0"
 bcc gd_alpha
 cmp #":"
 bcc gd_num
gd_alpha
 lda inbase
 cmp #BASE_HEX
 bne gd_bad
 lda inbuf,x
 cmp #"A"
 bcc gd_trylo
 cmp #"G"
 bcs gd_trylo
 sec
 sbc #"A"-10
 sec
 rts
gd_trylo
 lda inbuf,x
 cmp #"a"
 bcc gd_bad
 cmp #"g"
 bcs gd_bad
 sec
 sbc #"a"-10
 sec
 rts
gd_num
 sec
 sbc #"0"
 ldy inbase
 cmp maxdigp1,y
 bcs gd_bad
 sec
 rts
gd_bad
 clc
 rts

shl_value
 asl value32
 rol value32+1
 rol value32+2
 rol value32+3
 rts

add_digit_value
 clc
 adc value32
 sta value32
 lda value32+1
 adc #0
 sta value32+1
 lda value32+2
 adc #0
 sta value32+2
 lda value32+3
 adc #0
 sta value32+3
 rts

mul10_value
 lda value32
 sta tmp32
 lda value32+1
 sta tmp32+1
 lda value32+2
 sta tmp32+2
 lda value32+3
 sta tmp32+3
 jsr shl_value          ;value = original * 2
 bcs m10_bad
 jsr shl_tmp
 bcs m10_bad
 jsr shl_tmp
 bcs m10_bad
 jsr shl_tmp
 bcs m10_bad            ;tmp32 = original * 8
 clc
 lda value32
 adc tmp32
 sta value32
 lda value32+1
 adc tmp32+1
 sta value32+1
 lda value32+2
 adc tmp32+2
 sta value32+2
 lda value32+3
 adc tmp32+3
 sta value32+3
 rts
m10_bad
 sec
 rts

shl_tmp
 asl tmp32
 rol tmp32+1
 rol tmp32+2
 rol tmp32+3
 rts

value_gt_maxpos
 lda value32+3
 cmp #$7f
 bcc vgmp_no
 bne vgmp_yes
 lda value32+2
 cmp #$ff
 bcc vgmp_no
 bne vgmp_yes
 lda value32+1
 cmp #$ff
 bcc vgmp_no
 bne vgmp_yes
 lda value32
 cmp #$ff
 bcc vgmp_no
vgmp_no
 clc
 rts
vgmp_yes
 sec
 rts

value_gt_maxneg
 lda value32+3
 cmp #$80
 bcc vgmn_no
 bne vgmn_yes
 lda value32+2
 bne vgmn_yes
 lda value32+1
 bne vgmn_yes
 lda value32
 bne vgmn_yes
vgmn_no
 clc
 rts
vgmn_yes
 sec
 rts

negate_value
 lda value32
 eor #$ff
 sta value32
 lda value32+1
 eor #$ff
 sta value32+1
 lda value32+2
 eor #$ff
 sta value32+2
 lda value32+3
 eor #$ff
 sta value32+3
 clc
 lda value32
 adc #1
 sta value32
 lda value32+1
 adc #0
 sta value32+1
 lda value32+2
 adc #0
 sta value32+2
 lda value32+3
 adc #0
 sta value32+3
 rts

;==================== printing ====================
print_bin
 ldy #"%"
 lda #2
 jmp print_prefixed

print_oct
 ldy #"@"
 lda #8
 jmp print_prefixed

print_hex
 ldy #"$"
 lda #16
 ;fall through
print_prefixed
 sta basev
 sty prefixch
 jsr copy_value_to_work
 lda basev
 jsr conv_u32
 txa
 pha
 lda prefixch
 jsr CHROUT
 pla
 tax
 jmp print_digits_cr

print_dec
 jsr copy_value_to_work
 lda value32+3
 bpl pd_pos
 jsr negate_work
 lda #"-"
 jsr CHROUT
pd_pos
 lda #10
 jsr conv_u32
 jmp print_digits_cr

copy_value_to_work
 lda value32
 sta work32
 lda value32+1
 sta work32+1
 lda value32+2
 sta work32+2
 lda value32+3
 sta work32+3
 rts

negate_work
 lda work32
 eor #$ff
 sta work32
 lda work32+1
 eor #$ff
 sta work32+1
 lda work32+2
 eor #$ff
 sta work32+2
 lda work32+3
 eor #$ff
 sta work32+3
 clc
 lda work32
 adc #1
 sta work32
 lda work32+1
 adc #0
 sta work32+1
 lda work32+2
 adc #0
 sta work32+2
 lda work32+3
 adc #0
 sta work32+3
 rts

conv_u32
 sta basev
 ldy #0
 jsr work_is_zero
 beq cu_zero
cu_lp
 jsr divmod32
 lda rem
 jsr digitchr
 sta digbuf,y
 iny
 jsr work_is_zero
 bne cu_lp
 tya
 tax
 rts
cu_zero
 lda #"0"
 sta digbuf,y
 iny
 tya
 tax
 rts

work_is_zero
 lda work32
 ora work32+1
 ora work32+2
 ora work32+3
 rts

digitchr
 cmp #10
 bcc dgc_num
 clc
 adc #"a"-10
 rts
dgc_num
 clc
 adc #"0"
 rts

print_digits_cr
 dex
 bmi pdc_done
pdc_lp
 lda digbuf,x
 jsr CHROUT
 dex
 bpl pdc_lp
pdc_done
 lda #$0d
 jsr CHROUT
 rts

print_blank_line
 lda #$0d
 jsr CHROUT
 rts

divmod32
 lda #0
 sta quot32
 sta quot32+1
 sta quot32+2
 sta quot32+3
 sta rem
 ldx #32
dv_lp
 asl work32
 rol work32+1
 rol work32+2
 rol work32+3
 rol rem
 asl quot32
 rol quot32+1
 rol quot32+2
 rol quot32+3
 lda rem
 cmp basev
 bcc dv_next
 sec
 sbc basev
 sta rem
 inc quot32
dv_next
 dex
 bne dv_lp
 lda quot32
 sta work32
 lda quot32+1
 sta work32+1
 lda quot32+2
 sta work32+2
 lda quot32+3
 sta work32+3
 rts

;==================== strings ====================
prstrAY
 sta STRP
 sty STRP+1
 ldy #0
ps_lp
 lda (STRP),y
 beq ps_x
 jsr CHROUT
 iny
 bne ps_lp
ps_x
 rts

;==================== text ====================
;text is authored lowercase so tmpx emits PETSCII $41-$5a (unshifted uppercase),
;which CHROUT/the screen render as real uppercase letters.
hdrtxt
 .text "mdbasic convert"
 .byte $0d
 .text "enter %binary, @octal, $hex or decimal."
 .byte $0d
 .text "return converts. run/stop exits."
 .byte $0d, $0d, $00
serr .null "?invalid"

maxdigp1 .byte 2,8,16,10

;==================== state ====================
savnmi   .word 0
svd3     .byte 0
svd6     .byte 0
svpnt    .word 0
svhib    .byte 0
svbln    .byte 0
sav01    .byte 0
bufi     .byte 0
negflag  .byte 0
sawdig   .byte 0
inbase   .byte 0
digitv   .byte 0
basev    .byte 0
prefixch .byte 0
rem      .byte 0
value32  .byte 0,0,0,0
tmp32    .byte 0,0,0,0
work32   .byte 0,0,0,0
quot32   .byte 0,0,0,0
digbuf   .repeat 32,0
inbuf    .repeat 39,0
