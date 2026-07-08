; ***MDBASIC shared in-place BASIC edit tool***
; A full-screen REPL launched from the CTRL+RESTORE menu (R/M/C). Copied to $c000
; from its tool bank's $8000 and JSRed by the menu.asm $033c stub; RUN/STOP RTSs
; back to the stub, which does the NMI-tail RTI into the editor.
;
;   R [<inc>] [<start>] [<end>] [<dest>]
;                                -- partial renumber of the lines in the source
;                                   range, updating GOTO/GOSUB/ON/THEN/RUN/RESTORE/
;                                   RESUME/ELSE/ERRL= references in place. The new
;                                   numbering starts at <dest> if given, else <start>
;                                   (or <inc> if <start> is also omitted).
;   M <start> <end> <dest>       -- move+renumber a block, update its external
;                                   references, and relocate it to sorted order.
;   C <start> <end> <dest>       -- copy a block to a new, non-overlapping
;                                   destination (the destination range must not
;                                   overlap any existing line, including the
;                                   source range itself). Internal references
;                                   within the copy are retargeted to the new
;                                   numbers; the source block is left untouched,
;                                   so references elsewhere to it are unaffected.
;   RUN/STOP                     -- leave the tool.
;
; Every operation is validated by a pre-flight pass (below) that rejects a bad
; command BEFORE mutating anything, so a rejected R/M leaves the program byte-
; identical -- no scratch buffer / REU / rollback needed. It runs entirely with
; $01=$37 (BASIC+KERNAL+I/O in), so it can call ROM (LINKPRG/FRMNUM/FOUT/...)
; directly while it reads/writes program text in low RAM.
;
; The reference-rewrite scanner + in-place digit resize (nocrap/craper/tokgo/
; sav7a/numchr/inc2d/dec2d/bufer/pntreq/clrflg) is ported verbatim from MDBASIC's
; own RENUM (mdbasic.asm renumer pass 2); only the old->new line-number mapping is
; ours (`mapnum` replaces `replac`). Assembled for $c000 (run location).
;
; Screen/cursor/blink state is saved exactly once, by menu_body.asm, before this
; tool is ever copied to $c000 (see menu.asm's runmenu) -- this tool only
; restores it on exit, via the shared SAVD3/SAVD6/SAVPNT/SAVHIB/SAVBLN handoff.

; --- zero page / kernal / ROM ---
R6510    = $01
COUNT    = $0b
LINNUM   = $14
TXTTAB   = $2b
VARTAB   = $2d
ARYTAB   = $2f
STREND   = $31
OLDLIN   = $3b
TXTPTR   = $7a
XSAV     = $97
BLNSW    = $cc        ;cursor blink enable ($00=blinks, nonzero=disabled)
GDCHAR   = $ce
BLNON    = $cf
BLNCT    = $cd        ;cursor blink countdown (20 = one full period)
PNT      = $d1        ;pointer to the current screen line (lo/hi)
PNTR     = $d3        ;cursor column on the current line
TBLX     = $d6        ;cursor physical row
CHRGET   = $0073
CHRGOT   = $0079
BAD      = $0100      ;FOUT string work area (new-number ASCII lands here)
NMIVEC   = $0318
HIBASE   = $0288
SCREEN   = $0400
SCROLY   = $d011
VMCSB    = $d018
CI2PRA   = $dd00
CLRSCR   = $e544
LINKPRG  = $a533
RUNC     = $a68e
FRMNUM   = $ad8a
GETADR   = $b7f7
FOUT     = $bddd
INT2FLT  = $bc49      ;FAC1 = unsigned 16-bit int in $62/$63, exponent X
CHROUT   = $ffd2
GETIN    = $ffe4
LP       = $fb        ;line-walk pointer (validation / header / map / relocate)
ACC      = $fd        ;renumber accumulator
RVA      = $22        ;reverse pointers (shared with the ported resize engine)
RVB      = $24        ;($22-$25 are free outside refpass)
STRP     = $26        ;print-string pointer

TOKEN_ERR   = $f2
TOKEN_EQUAL = $b2

SCRBUF   = $cc00      ;1K snapshot of screen RAM ($0400-$07ff), saved once by
                      ;menu_body.asm before this tool is copied in, restored by
                      ;this tool on exit -- same idiom/address as the docs
                      ;pager's SCRBUF. Free scratch above the $c000 tool image
                      ;and below I/O; outside the copied image so it costs no
                      ;cart budget.

;--- shared CTRL+RESTORE-menu screen/cursor/blink handoff (see menu_body.asm) ---
;menu_body.asm always runs before this tool (either its full F1/R/M/C/STOP UI, via
;the real CTRL+RESTORE path, or its quick save-only path, via menu.asm's dorenum
;test-bypass entry) and populates these before copying this tool over $c000, so
;this tool never does its own entry-side save -- only the matching exit-side
;restore. Zero page: menu.asm's copyrun scratch ($02-$05,$fb-$fe) is transient
;and expires before this tool runs; these addresses also avoid this tool's own
;persistent zero page (COUNT $0b, LINNUM $14, TXTTAB $2b, etc. below).
SAVD3    = $06        ;saved PNTR (cursor column)
SAVD6    = $07        ;saved TBLX (cursor row)
SAVPNT   = $08        ;saved PNT lo($08)/hi($09)
SAVHIB   = $0a        ;saved HIBASE (screen page at CTRL+RESTORE time)
SAVBLN   = $0d        ;saved BLNSW (blink-enable state at CTRL+RESTORE time)

.ifndef TOOL_MOVE
.ifndef TOOL_COPY
.ifndef TOOL_RENUM
TOOL_RENUM = 1
.endif
.endif
.endif
.ifdef TOOL_MOVE
TOOL_REMAP = 1
.endif
.ifdef TOOL_COPY
TOOL_REMAP = 1
.endif

*=$c000

;==================== entry ====================
start
 lda R6510
 sta sav01
 lda #$37
 sta R6510            ;BASIC+KERNAL+I/O in (ROM callable, program text in RAM)
 lda #1
 sta BLNSW            ;disable cursor blink for the session -- the REPL has no
                      ;screen-editor cursor to move, so blinking one would be
                      ;misleading (input is GETIN+CHROUT, not the line editor).
                      ;The true original blink-enable state is already saved in
                      ;SAVBLN by menu_body.asm.
 lda NMIVEC
 sta savnmi
 lda NMIVEC+1
 sta savnmi+1
 lda #<nmistub        ;neutralise RESTORE while the tool owns the screen
 sta NMIVEC
 lda #>nmistub
 sta NMIVEC+1
 jsr forcetext        ;canonical text mode / VIC bank 0 (in case graphics was on)
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
 jsr exec
 jsr prresult
 jmp repl

;==================== exit ====================
;If we came from the $0400 text screen (savhib = $04), the snapshot taken at
;entry is the real pre-tool screen: put it back verbatim (no CLRSCR, so the
;editor's line-link table stays consistent with the restored PNT/cursor).
;If we came from a SCREEN 1-5 page (savhib != $04), that page's content was
;never saved (SCRBUF only holds $0400) and its line-link table + PNT still
;point at it, so just clear to a fresh $0400 screen instead -- identical to
;the docs pager's SCREEN-1-5 exit handling.
texit
 lda savnmi
 sta NMIVEC
 lda savnmi+1
 sta NMIVEC+1
 lda SAVHIB
 cmp #$04
 bne tblank
 jsr forcetext
 jsr restorescreen    ;put the saved screen RAM + cursor position back
 lda SAVBLN
 sta BLNSW            ;resume the prior blink-enable state
 lda #$ff
 sta BLNON            ;char-shown phase: the resumed IRQ draws a fresh cursor
                      ;block, leaving no stale block artifact
 lda #1
 sta BLNCT            ;blink almost immediately
 lda sav01
 sta R6510
 rts                  ;-> menu.asm stub does the NMI-tail RTI
tblank
 jsr forcetext
 sei                  ;mask the blink IRQ across the clear + cursor reset (U64 race,
                      ;same care as the docs pager's SCREEN-1-5 exit)
 jsr CLRSCR
 lda #$20
 sta GDCHAR
 lda SAVBLN
 sta BLNSW            ;resume the prior blink-enable state
 lda #$ff
 sta BLNON
 lda sav01
 sta R6510
 rts                  ;-> menu.asm stub does the NMI-tail RTI

nmistub
 rti

;force canonical text screen (identical idiom to SCREEN 0's pgzero in mdbasic.asm)
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
;Restores the snapshot menu_body.asm took before this tool was copied in (see
;the SAVD3/SAVD6/SAVPNT handoff equates above). This tool calls CLRSCR itself
;(to draw its own REPL screen), which homes PNT/PNTR/TBLX -- so PNT must be
;restored here too, not just PNTR/TBLX like the docs pager.
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
 lda SAVD3
 sta PNTR
 lda SAVD6
 sta TBLX
 lda SAVPNT
 sta PNT
 lda SAVPNT+1
 sta PNT+1
 rts

;==================== line input ====================
;read a line into inbuf (null-terminated). C=1 on RUN/STOP (leave the tool),
;C=0 on RETURN. X returns the length.
;NOTE: GETIN (kernal) clobbers X and Y, so the buffer index is kept in `bufi`,
;not a register, across the read loop.
readline
 lda #0
 sta bufi
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
 bcc rl_lp            ;$80-$9f: shifted control codes (cursor keys, RVS,
                      ;colour keys, f-keys) -- ignore so cursor keys can't
                      ;move the (invisible) cursor around the screen
rl_ok
 ldx bufi
 cpx #38
 bcs rl_lp            ;buffer full
 sta inbuf,x
 jsr CHROUT           ;echo
 inc bufi
 jmp rl_lp
rl_del
 lda bufi
 beq rl_lp
 dec bufi
 lda #$14
 jsr CHROUT           ;erase on screen
 jmp rl_lp
rl_done
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

;==================== command parse / dispatch ====================
;exec: parse inbuf, run the command, leave a code in resultcode.
exec
 lda #$ff
 sta resultcode       ;default: print nothing (blank line)
 ldx #0
 jsr skipsp
 lda inbuf,x
.ifdef TOOL_RENUM
 beq ex_done          ;empty line -> nothing
 cmp #"r"             ;lowercase literal = PETSCII $52 = the unshifted 'R' key
 beq ex_renum
 jmp ex_renum_args    ;bare args are accepted in the single-command tool
.endif
.ifdef TOOL_MOVE
 cmp #0
 beq ex_done          ;empty line -> nothing
 cmp #"m"
 beq ex_move
 jmp ex_move_args     ;bare args are accepted in the single-command tool
.endif
.ifdef TOOL_COPY
 cmp #0
 beq ex_done          ;empty line -> nothing
 cmp #"c"
 beq ex_copy
 jmp ex_copy_args     ;bare args are accepted in the single-command tool
.endif
 lda #1
 sta resultcode       ;?SYNTAX
ex_done
 rts

.ifdef TOOL_RENUM
ex_renum
 inx                  ;skip R
ex_renum_args
 lda #0
 sta op
 lda #10              ;defaults: inc=10, base=10, lo=0, end=63999
 sta inc16
 sta base16
 lda #0
 sta inc16+1
 sta base16+1
 sta lo16
 sta lo16+1
 lda #<63999
 sta end16
 lda #>63999
 sta end16+1
 jsr getnum
 bcc erun             ;no args -> defaults
 lda numbuf
 sta inc16
 sta base16
 lda numbuf+1
 sta inc16+1
 sta base16+1
 lda inc16
 ora inc16+1
 bne er2
 lda #1
 sta resultcode       ;inc 0 -> ?SYNTAX
 rts
er2
 jsr getnum
 bcc erun             ;inc only
 lda numbuf           ;start given -> lo=start, base=start
 sta lo16
 sta base16
 lda numbuf+1
 sta lo16+1
 sta base16+1
 jsr getnum
 bcc erun
 lda numbuf
 sta end16
 lda numbuf+1
 sta end16+1
 jsr getnum
 bcc erun             ;no dest -> base stays start (or inc, per above)
 lda numbuf           ;dest given -> override base (new numbering starts here)
 sta base16
 lda numbuf+1
 sta base16+1
erun
 jmp do_renum
.endif

.ifdef TOOL_MOVE
ex_move
 inx                  ;skip M
ex_move_args
 lda #1
 sta op
 jsr getnum
 bcc ex_syn
 lda numbuf
 sta mstart
 lda numbuf+1
 sta mstart+1
 jsr getnum
 bcc ex_syn
 lda numbuf
 sta mend
 lda numbuf+1
 sta mend+1
 jsr getnum
 bcc ex_syn
 lda numbuf
 sta mdest
 lda numbuf+1
 sta mdest+1
 jmp do_move
.endif
ex_syn
 lda #1
 sta resultcode
 rts

.ifdef TOOL_COPY
ex_copy
 inx                  ;skip C
ex_copy_args
 lda #2
 sta op
 jsr getnum
 bcc ex_syn
 lda numbuf
 sta mstart
 lda numbuf+1
 sta mstart+1
 jsr getnum
 bcc ex_syn
 lda numbuf
 sta mend
 lda numbuf+1
 sta mend+1
 jsr getnum
 bcc ex_syn
 lda numbuf
 sta mdest
 lda numbuf+1
 sta mdest+1
 jmp do_copy
.endif

;skipsp: advance X over spaces in inbuf
skipsp
 lda inbuf,x
 cmp #$20
 bne sk_x
 inx
 bne skipsp
sk_x
 rts

;getnum: parse a decimal number at inbuf,x into numbuf. C=1 if a digit was read.
getnum
 jsr skipsp
 lda #0
 sta numbuf
 sta numbuf+1
 ldy #0               ;digit count
gn_lp
 lda inbuf,x
 cmp #"0"
 bcc gn_end
 cmp #":"             ;'9'+1
 bcs gn_end
 pha
 jsr mul10
 pla
 sec
 sbc #"0"
 clc
 adc numbuf
 sta numbuf
 bcc gn_c
 inc numbuf+1
gn_c
 inx
 iny
 bne gn_lp
gn_end
 cpy #0
 beq gn_none
 sec
 rts
gn_none
 clc
 rts

;numbuf = numbuf * 10  (n*8 + n*2)
mul10
 lda numbuf
 sta tmpm
 lda numbuf+1
 sta tmpm+1
 asl numbuf
 rol numbuf+1         ;n*2
 lda numbuf
 sta tmpn
 lda numbuf+1
 sta tmpn+1           ;save n*2
 asl numbuf
 rol numbuf+1         ;n*4
 asl numbuf
 rol numbuf+1         ;n*8
 clc
 lda numbuf
 adc tmpn
 sta numbuf
 lda numbuf+1
 adc tmpn+1
 sta numbuf+1
 rts

;==================== result reporting ====================
prresult
 lda resultcode
 cmp #$ff
 beq prr_x
 asl                  ;*2 index into the pointer table
 tax
 lda restab,x
 ldy restab+1,x
 jsr prstrAY
 lda #$0d
 jsr CHROUT
prr_x
 rts

;prstrAY: print the null-terminated PETSCII string at A(lo)/Y(hi).
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

;==================== RENUM ====================
.ifdef TOOL_RENUM
do_renum
 jsr val_renum
 lda resultcode
 bne dr_x             ;error / no-op -> no mutation
 jsr refpass          ;rewrite references in place (headers still original)
 jsr relink
 jsr hdr_renum        ;renumber the line headers (size-neutral)
 jsr relink
 jsr finishop
 lda #0
 sta resultcode       ;OK
dr_x
 rts

;val_renum: pre-flight. Sets resultcode (0 ok / 2 range / 3 collision / 4 none).
val_renum
 lda #0
 sta scount
 sta scount+1
 sta haveb
 sta havea
 jsr set_rrange       ;rlo=lo16, rhi=end16
 jsr lp_first
vr_lp
 jsr lp_num           ;curnum = (LP) number; Z=1 at end of program
 beq vr_end
 jsr in_range
 bcs vr_src
 ;kept line: below the block (curnum<lo16) or above it
 lda lo16
 sta rlo
 lda lo16+1
 sta rlo+1
 jsr cmp_cur_rlo      ;C=curnum>=lo16
 bcs vr_above
 lda curnum           ;below -> remember the largest kept line under the block
 sta beforeN
 lda curnum+1
 sta beforeN+1
 lda #1
 sta haveb
 jmp vr_next
vr_above
 lda havea
 bne vr_next          ;keep only the FIRST kept line above the block
 lda curnum
 sta afterN
 lda curnum+1
 sta afterN+1
 lda #1
 sta havea
 jmp vr_next
vr_src
 inc scount
 bne vr_next
 inc scount+1
vr_next
 jsr lp_next
 jmp vr_lp
vr_end
 lda scount
 ora scount+1
 bne vr_have
 lda #4               ;NO LINES
 sta resultcode
 rts
vr_have
 ;lastnew = base + inc*(scount-1); reject if any value > 63999
 lda base16
 sta lastnew
 lda base16+1
 sta lastnew+1
 lda base16+1
 cmp #$fa
 bcc vr_b_ok
 jmp vr_range         ;base itself > 63999
vr_b_ok
 lda scount
 sec
 sbc #1
 sta cnt
 lda scount+1
 sbc #0
 sta cnt+1
vr_mul
 lda cnt
 ora cnt+1
 beq vr_order
 clc
 lda lastnew
 adc inc16
 sta lastnew
 lda lastnew+1
 adc inc16+1
 sta lastnew+1
 bcc vr_m_nc
 jmp vr_range         ;carry out of 16 bits -> way over 63999
vr_m_nc
 lda lastnew+1
 cmp #$fa
 bcc vr_m_ok
 jmp vr_range
vr_m_ok
 lda cnt
 sec
 sbc #1
 sta cnt
 lda cnt+1
 sbc #0
 sta cnt+1
 jmp vr_mul
vr_order
 lda haveb
 beq vr_ck_after
 ;base must be > beforeN
 lda base16
 sta curnum
 lda base16+1
 sta curnum+1
 lda beforeN
 sta rlo
 lda beforeN+1
 sta rlo+1
 jsr cmp_cur_rlo      ;C=base>=beforeN, Z=equal
 bcc vr_coll
 beq vr_coll
vr_ck_after
 lda havea
 beq vr_ok
 ;lastnew must be < afterN
 lda lastnew
 sta curnum
 lda lastnew+1
 sta curnum+1
 lda afterN
 sta rlo
 lda afterN+1
 sta rlo+1
 jsr cmp_cur_rlo      ;C=lastnew>=afterN
 bcs vr_coll
vr_ok
 lda #0
 sta resultcode
 rts
vr_range
 lda #2
 sta resultcode
 rts
vr_coll
 lda #3
 sta resultcode
 rts

;hdr_renum: write the new sequential numbers into the source lines' headers.
hdr_renum
 lda base16
 sta ACC
 lda base16+1
 sta ACC+1
 jsr set_rrange
 jsr lp_first
hr_lp
 jsr lp_num
 beq hr_x
 jsr in_range
 bcc hr_next
 ldy #2
 lda ACC
 sta (LP),y
 iny
 lda ACC+1
 sta (LP),y
 clc
 lda ACC
 adc inc16
 sta ACC
 lda ACC+1
 adc inc16+1
 sta ACC+1
hr_next
 jsr lp_next
 jmp hr_lp
hr_x
 rts
.endif

;==================== MOVE ====================
.ifdef TOOL_MOVE
do_move
 ;require end >= start (a single line is a valid move)
 lda mend+1
 cmp mstart+1
 bcc dm_bad
 bne dm_ok1
 lda mend
 cmp mstart
 bcc dm_bad
dm_ok1
 jsr val_move
 lda resultcode
 bne dm_x
 jsr refpass
 jsr relink
 jsr hdr_move
 jsr mv_reloc
 jsr relink
 jsr finishop
 lda #0
 sta resultcode
dm_x
 rts
dm_bad
 lda #5               ;END<START
 sta resultcode
 rts

;val_move: compute new range, reject overflow / interleave-collision.
val_move
 lda #0
 sta scount
 sta scount+1
 jsr set_mrange       ;rlo=mstart, rhi=mend
 jsr lp_first
vm_lp
 jsr lp_num
 beq vm_endw
 jsr in_range
 bcc vm_next
 lda scount
 ora scount+1
 bne vm_nf
 lda curnum           ;first source -> minsrc
 sta minsrc
 lda curnum+1
 sta minsrc+1
vm_nf
 lda curnum           ;last source seen -> maxsrc
 sta maxsrc
 lda curnum+1
 sta maxsrc+1
 inc scount
 bne vm_next
 inc scount+1
vm_next
 jsr lp_next
 jmp vm_lp
vm_endw
 lda scount
 ora scount+1
 bne vm_have
 lda #4               ;NO LINES
 sta resultcode
 rts
vm_have
 ;newmin = mdest (first source line lands exactly on dest);
 ;newmax = maxsrc - minsrc + mdest
 lda mdest
 sta newmin
 lda mdest+1
 sta newmin+1
 sec
 lda maxsrc
 sbc minsrc
 sta newmax
 lda maxsrc+1
 sbc minsrc+1
 sta newmax+1
 clc
 lda newmax
 adc mdest
 sta newmax
 lda newmax+1
 adc mdest+1
 sta newmax+1
 bcs vm_range         ;carry out of 16 bits -> > 63999
 lda newmax+1
 cmp #$fa
 bcs vm_range         ;> 63999
 ;interleave/collision: any non-source line with num in [newmin,newmax]?
 jsr lp_first
vm_clp
 jsr lp_num
 beq vm_ok
 jsr set_mrange
 jsr in_range
 bcs vm_cnext         ;source line -> skip
 jsr set_nrange       ;rlo=newmin, rhi=newmax
 jsr in_range
 bcs vm_coll
vm_cnext
 jsr lp_next
 jmp vm_clp
vm_ok
 lda #0
 sta resultcode
 rts
vm_range
 lda #2
 sta resultcode
 rts
vm_coll
 lda #3
 sta resultcode
 rts

;hdr_move: header = curnum - minsrc + mdest for each source line (so the first
;source line, curnum=minsrc, lands exactly on mdest).
hdr_move
 jsr set_mrange
 jsr lp_first
hm_lp
 jsr lp_num
 beq hm_x
 jsr in_range
 bcc hm_next
 sec
 lda curnum
 sbc minsrc
 sta t16
 lda curnum+1
 sbc minsrc+1
 sta t16+1
 clc
 lda t16
 adc mdest
 sta t16
 lda t16+1
 adc mdest+1
 sta t16+1
 ldy #2
 lda t16
 sta (LP),y
 iny
 lda t16+1
 sta (LP),y
hm_next
 jsr lp_next
 jmp hm_lp
hm_x
 rts

;mv_reloc: relocate the moved block to sorted position by swapping it with the
;adjacent run of kept lines it must leapfrog (3-reversal block swap, in place).
mv_reloc
 jsr set_nrange       ;rlo=newmin, rhi=newmax (block's new numbers)
 jsr lp_first
mr_f0
 jsr lp_num
 bne mr_f0c
 jmp mr_x             ;no block found (shouldn't happen) -> nothing to do
mr_f0c
 jsr in_range
 bcs mr_p0
 jsr lp_next
 jmp mr_f0
mr_p0
 lda LP
 sta P0
 lda LP+1
 sta P0+1
mr_f1
 jsr lp_next
 jsr lp_num
 beq mr_p1            ;end of program -> P1 here
 jsr in_range
 bcs mr_f1
mr_p1
 lda LP
 sta P1
 lda LP+1
 sta P1+1
 ;INS = first line (from start) with num > newmax
 jsr lp_first
mr_ins
 jsr lp_num
 beq mr_haveins       ;end -> append point
 lda newmax
 sta rlo
 lda newmax+1
 sta rlo+1
 jsr cmp_cur_rlo      ;C=curnum>=newmax, Z=equal
 bcc mr_insn          ;curnum<newmax
 beq mr_insn          ;curnum==newmax (a block line) -> keep scanning
 jmp mr_haveins       ;curnum>newmax
mr_insn
 jsr lp_next
 jmp mr_ins
mr_haveins
 lda LP
 sta INSp
 lda LP+1
 sta INSp+1
 ;compare INSp with P1
 lda INSp+1
 cmp P1+1
 bne mr_c1
 lda INSp
 cmp P1
mr_c1
 beq mr_x             ;INSp==P1 -> already sorted
 bcs mr_fwd           ;INSp>P1
 ;INSp<P1: compare with P0
 lda INSp+1
 cmp P0+1
 bne mr_c2
 lda INSp
 cmp P0
mr_c2
 bcs mr_x             ;P0<=INSp<P1 -> within block, no move
 ;INSp<P0 -> swap [INSp,P0) with [P0,P1)
 lda INSp
 sta swA
 lda INSp+1
 sta swA+1
 lda P0
 sta swB
 lda P0+1
 sta swB+1
 lda P1
 sta swC
 lda P1+1
 sta swC+1
 jmp swap3
mr_fwd
 ;swap [P0,P1) with [P1,INSp)
 lda P0
 sta swA
 lda P0+1
 sta swA+1
 lda P1
 sta swB
 lda P1+1
 sta swB+1
 lda INSp
 sta swC
 lda INSp+1
 sta swC+1
 jmp swap3
mr_x
 rts

;swap3: swap adjacent byte regions [swA,swB) and [swB,swC) (rotate) in place.
swap3
 lda swA
 sta rstart
 lda swA+1
 sta rstart+1
 lda swB
 sta rend
 lda swB+1
 sta rend+1
 jsr reverse
 lda swB
 sta rstart
 lda swB+1
 sta rstart+1
 lda swC
 sta rend
 lda swC+1
 sta rend+1
 jsr reverse
 lda swA
 sta rstart
 lda swA+1
 sta rstart+1
 lda swC
 sta rend
 lda swC+1
 sta rend+1
 jmp reverse

;reverse the bytes in [rstart, rend)
reverse
 lda rstart
 sta RVA
 lda rstart+1
 sta RVA+1
 lda rend
 sec
 sbc #1
 sta RVB
 lda rend+1
 sbc #0
 sta RVB+1
rv_lp
 lda RVA+1
 cmp RVB+1
 bcc rv_go
 bne rv_x
 lda RVA
 cmp RVB
 bcs rv_x
rv_go
 ldy #0
 lda (RVA),y
 pha
 lda (RVB),y
 sta (RVA),y
 pla
 sta (RVB),y
 inc RVA
 bne rv_a
 inc RVA+1
rv_a
 lda RVB
 bne rv_b
 dec RVB+1
rv_b
 dec RVB
 jmp rv_lp
rv_x
 rts
.endif

;==================== COPY ====================
.ifdef TOOL_COPY
do_copy
 ;require end >= start (a single line is a valid copy)
 lda mend+1
 cmp mstart+1
 bcc dc_bad
 bne dc_ok1
 lda mend
 cmp mstart
 bcc dc_bad
dc_ok1
 jsr val_copy
 lda resultcode
 bne dc_x
 jsr cp_reserve        ;open a blocklen gap at the sorted dest position and
                       ;duplicate the source block's raw bytes into it
 jsr refpass_blk       ;retarget internal GOTO/etc refs (source range -> dest),
                       ;scoped to just the new copy -- resizes in place as needed
 jsr hdr_copy          ;renumber the copy's own line headers
 jsr relink
 jsr finishop
 lda #0
 sta resultcode
dc_x
 rts
dc_bad
 lda #5                ;END<START
 sta resultcode
 rts

;val_copy: pre-flight. Like val_move's scan (finds minsrc/maxsrc/scount over
;[mstart,mend] and computes newmin/newmax = mdest.. mdest+(maxsrc-minsrc)), but
;the collision check does NOT skip source-range lines -- a copy leaves the
;source in place, so the destination must not overlap it either.
val_copy
 lda #0
 sta scount
 sta scount+1
 jsr set_mrange        ;rlo=mstart, rhi=mend
 jsr lp_first
vc_lp
 jsr lp_num
 beq vc_endw
 jsr in_range
 bcc vc_next
 lda scount
 ora scount+1
 bne vc_nf
 lda curnum
 sta minsrc
 lda curnum+1
 sta minsrc+1
vc_nf
 lda curnum
 sta maxsrc
 lda curnum+1
 sta maxsrc+1
 inc scount
 bne vc_next
 inc scount+1
vc_next
 jsr lp_next
 jmp vc_lp
vc_endw
 lda scount
 ora scount+1
 bne vc_have
 lda #4                ;NO LINES
 sta resultcode
 rts
vc_have
 lda mdest
 sta newmin
 lda mdest+1
 sta newmin+1
 sec
 lda maxsrc
 sbc minsrc
 sta newmax
 lda maxsrc+1
 sbc minsrc+1
 sta newmax+1
 clc
 lda newmax
 adc mdest
 sta newmax
 lda newmax+1
 adc mdest+1
 sta newmax+1
 bcs vc_range          ;carry out of 16 bits -> > 63999
 lda newmax+1
 cmp #$fa
 bcs vc_range
 ;collision: ANY line (including the source range) with num in [newmin,newmax]?
 jsr lp_first
vc_clp
 jsr lp_num
 beq vc_ok
 jsr set_nrange        ;rlo=newmin, rhi=newmax
 jsr in_range
 bcs vc_coll
 jsr lp_next
 jmp vc_clp
vc_ok
 lda #0
 sta resultcode
 rts
vc_range
 lda #2
 sta resultcode
 rts
vc_coll
 lda #3
 sta resultcode
 rts

;cp_reserve: find the source block [P0,P1) and the sorted insertion point
;(blkstart = first line's address with num > newmax, or end-of-program), open a
;blocklen-byte gap there by shifting [blkstart,STREND) up in one descending pass,
;bump VARTAB/ARYTAB/STREND by blocklen (so refpass_blk's own inc2d/dec2d growth
;shifts against the correct new top), then duplicate the source block's raw
;bytes (still bearing the OLD headers/numbers) into the gap.
cp_reserve
 jsr set_mrange
 jsr lp_first
cpr_f0
 jsr lp_num
 bne cpr_f0c
 rts                   ;can't happen -- val_copy already confirmed lines exist
cpr_f0c
 jsr in_range
 bcs cpr_p0
 jsr lp_next
 jmp cpr_f0
cpr_p0
 lda LP
 sta P0
 lda LP+1
 sta P0+1
cpr_f1
 jsr lp_next
 jsr lp_num
 beq cpr_p1            ;end of program -> P1 here
 jsr in_range
 bcs cpr_f1
cpr_p1
 lda LP
 sta P1
 lda LP+1
 sta P1+1
 sec
 lda P1
 sbc P0
 sta blocklen
 lda P1+1
 sbc P0+1
 sta blocklen+1
 jsr lp_first
cpr_ins
 jsr lp_num
 beq cpr_haveins        ;end -> append point
 lda newmax
 sta rlo
 lda newmax+1
 sta rlo+1
 jsr cmp_cur_rlo        ;C=curnum>=newmax, Z=equal
 bcc cpr_insn
 beq cpr_insn
 jmp cpr_haveins
cpr_insn
 jsr lp_next
 jmp cpr_ins
cpr_haveins
 lda LP
 sta blkstart
 lda LP+1
 sta blkstart+1
 ;srcpost = (P0 >= blkstart) ? P0+blocklen : P0 -- where the source's original
 ;bytes end up once the shift below moves everything from blkstart upward
 lda P0+1
 cmp blkstart+1
 bne cpr_cmp1
 lda P0
 cmp blkstart
cpr_cmp1
 bcc cpr_nomove
 clc
 lda P0
 adc blocklen
 sta srcpost
 lda P0+1
 adc blocklen+1
 sta srcpost+1
 jmp cpr_havesrc
cpr_nomove
 lda P0
 sta srcpost
 lda P0+1
 sta srcpost+1
cpr_havesrc
 ;shift [blkstart,STREND) up by blocklen bytes, high-to-low (RVA=src, RVB=dst)
 sec
 lda STREND
 sbc blkstart
 sta cnt
 lda STREND+1
 sbc blkstart+1
 sta cnt+1
 lda STREND
 sec
 sbc #1
 sta RVA
 lda STREND+1
 sbc #0
 sta RVA+1
 clc
 lda RVA
 adc blocklen
 sta RVB
 lda RVA+1
 adc blocklen+1
 sta RVB+1
cpr_shlp
 lda cnt
 ora cnt+1
 beq cpr_shdone
 ldy #0
 lda (RVA),y
 sta (RVB),y
 lda RVA
 bne cpr_s1
 dec RVA+1
cpr_s1
 dec RVA
 lda RVB
 bne cpr_s2
 dec RVB+1
cpr_s2
 dec RVB
 sec
 lda cnt
 sbc #1
 sta cnt
 lda cnt+1
 sbc #0
 sta cnt+1
 jmp cpr_shlp
cpr_shdone
 clc
 lda VARTAB
 adc blocklen
 sta VARTAB
 lda VARTAB+1
 adc blocklen+1
 sta VARTAB+1
 clc
 lda ARYTAB
 adc blocklen
 sta ARYTAB
 lda ARYTAB+1
 adc blocklen+1
 sta ARYTAB+1
 clc
 lda STREND
 adc blocklen
 sta STREND
 lda STREND+1
 adc blocklen+1
 sta STREND+1
 ;duplicate the raw source bytes into the freshly opened gap
 lda srcpost
 sta RVA
 lda srcpost+1
 sta RVA+1
 lda blkstart
 sta RVB
 lda blkstart+1
 sta RVB+1
 lda blocklen
 sta t16
 lda blocklen+1
 sta t16+1
cpr_cplp
 lda t16
 ora t16+1
 beq cpr_x
 ldy #0
 lda (RVA),y
 sta (RVB),y
 inc RVA
 bne cpr_c1
 inc RVA+1
cpr_c1
 inc RVB
 bne cpr_c2
 inc RVB+1
cpr_c2
 sec
 lda t16
 sbc #1
 sta t16
 lda t16+1
 sbc #0
 sta t16+1
 jmp cpr_cplp
cpr_x
 rts

;hdr_copy: rewrite the duplicate's own line headers to the new sequential
;numbers (curheader - minsrc + mdest), walking exactly scount lines by content-
;scan (lp_next_scan) since the duplicate's link fields are still stale copies
;of the originals' until the next relink.
hdr_copy
 lda blkstart
 sta LP
 lda blkstart+1
 sta LP+1
 lda scount
 sta cnt
 lda scount+1
 sta cnt+1
hc_lp
 lda cnt
 ora cnt+1
 beq hc_x
 sec
 lda cnt
 sbc #1
 sta cnt
 lda cnt+1
 sbc #0
 sta cnt+1
 ldy #2
 lda (LP),y
 sec
 sbc minsrc
 sta t16
 iny
 lda (LP),y
 sbc minsrc+1
 sta t16+1
 clc
 lda t16
 adc mdest
 sta t16
 lda t16+1
 adc mdest+1
 sta t16+1
 ldy #2
 lda t16
 sta (LP),y
 iny
 lda t16+1
 sta (LP),y
 jsr lp_next_scan
 jmp hc_lp
hc_x
 rts
.endif

;==================== old->new mapping (called by the ported scanner) ====================
;mapnum: LINNUM = a referenced line number. Produce its new-number ASCII string in
;BAD ($0100) via fltstr. Free to clobber LP/ACC (the scanner restores TXTPTR).
mapnum
;--- renumber ---
.ifdef TOOL_RENUM
 lda LINNUM
 sta curnum
 lda LINNUM+1
 sta curnum+1
 jsr set_rrange
 jsr in_range
 bcs mn_r_in
 jmp mn_keep          ;ref outside the source range -> unchanged
mn_r_in
 lda base16
 sta ACC
 lda base16+1
 sta ACC+1
 lda #0
 sta mfound
 jsr lp_first
mn_wlp
 jsr lp_num
 beq mn_wend
 jsr in_range
 bcc mn_wnext         ;non-source line
 jsr cmp_cur_ln       ;curnum vs LINNUM
 beq mn_hit
 bcs mn_wend          ;passed LINNUM without a match -> dangling ref
 clc
 lda ACC
 adc inc16
 sta ACC
 lda ACC+1
 adc inc16+1
 sta ACC+1
mn_wnext
 jsr lp_next_scan     ;links are stale mid-refpass -> walk by scanning
 jmp mn_wlp
mn_hit
 lda #1
 sta mfound
mn_wend
 lda mfound
 beq mn_keep          ;dangling -> leave the reference unchanged
 lda ACC
 sta t16
 lda ACC+1
 sta t16+1
 jmp mn_emit
.endif
.ifdef TOOL_REMAP
mn_move
 lda LINNUM
 sta curnum
 lda LINNUM+1
 sta curnum+1
 jsr set_mrange
 jsr in_range
 bcc mn_keep          ;ref outside the moved block -> unchanged
 sec                  ;new = LINNUM - minsrc + mdest
 lda LINNUM
 sbc minsrc
 sta t16
 lda LINNUM+1
 sbc minsrc+1
 sta t16+1
 clc
 lda t16
 adc mdest
 sta t16
 lda t16+1
 adc mdest+1
 sta t16+1
 jmp mn_emit
.endif
mn_keep
 lda LINNUM
 sta t16
 lda LINNUM+1
 sta t16+1
mn_emit
 lda t16+1
 sta $62
 lda t16
 sta $63
;fall into fltstr

;fltstr: unsigned int in $62(hi)/$63(lo) -> ASCII at BAD (ROM already paged in).
fltstr
 ldx #$90
 sec
 jsr INT2FLT
 jsr FOUT+2           ;FAC1 -> string at $0100, no leading space
 rts

;==================== line-walk helpers (LP) ====================
lp_first
 lda TXTTAB
 sta LP
 lda TXTTAB+1
 sta LP+1
 rts
;lp_num: curnum = this line's number; Z=1 (via link hi==0) at end of program.
lp_num
 ldy #1
 lda (LP),y
 beq lp_num_end
 dey
 lda (LP),y           ;(harmless read; keeps Z clear via the number load below)
 ldy #2
 lda (LP),y
 sta curnum
 ldy #3
 lda (LP),y
 sta curnum+1
 ldy #1               ;return Z=0 (not end): link hi is nonzero
 lda (LP),y
lp_num_end
 rts
;lp_next: LP = this line's link (address of the next line). Valid only when the
;line links are intact (validation / after a relink).
lp_next
 ldy #0
 lda (LP),y
 tax
 iny
 lda (LP),y
 stx LP
 sta LP+1
 rts
;lp_next_scan: advance LP to the next line WITHOUT trusting the link -- skip the
;4-byte header, then scan the body to its $00 terminator. Used by mapnum during
;refpass, when inc2d/dec2d resizes have left the links stale (relink comes later).
lp_next_scan
 lda LP
 clc
 adc #4
 sta LP
 lda LP+1
 adc #0
 sta LP+1
lns_scan
 ldy #0
 lda (LP),y
 beq lns_done
 inc LP
 bne lns_scan
 inc LP+1
 jmp lns_scan
lns_done
 inc LP
 bne lns_x
 inc LP+1
lns_x
 rts

;==================== 16-bit range / compare helpers ====================
set_rrange
 lda lo16
 sta rlo
 lda lo16+1
 sta rlo+1
 lda end16
 sta rhi
 lda end16+1
 sta rhi+1
 rts
set_mrange
 lda mstart
 sta rlo
 lda mstart+1
 sta rlo+1
 lda mend
 sta rhi
 lda mend+1
 sta rhi+1
 rts
set_nrange
 lda newmin
 sta rlo
 lda newmin+1
 sta rlo+1
 lda newmax
 sta rhi
 lda newmax+1
 sta rhi+1
 rts
;in_range: C=1 if rlo <= curnum <= rhi (unsigned)
in_range
 lda curnum+1
 cmp rlo+1
 bcc ir_no
 bne ir_hi
 lda curnum
 cmp rlo
 bcc ir_no
ir_hi
 lda rhi+1
 cmp curnum+1
 bcc ir_no
 bne ir_yes
 lda rhi
 cmp curnum
 bcc ir_no
ir_yes
 sec
 rts
ir_no
 clc
 rts
;cmp_cur_rlo: flags for curnum - rlo (Z=equal, C=curnum>=rlo)
cmp_cur_rlo
 lda curnum+1
 cmp rlo+1
 bne cr_x
 lda curnum
 cmp rlo
cr_x
 rts
;cmp_cur_ln: flags for curnum - LINNUM (Z=equal, C=curnum>=LINNUM)
cmp_cur_ln
 lda curnum+1
 cmp LINNUM+1
 bne cl_x
 lda curnum
 cmp LINNUM
cl_x
 rts

;==================== finish an operation ====================
;relink: LINKPRG rebuilds the line links; VARTAB/ARYTAB/STREND follow (old2 idiom).
relink
 jsr LINKPRG
 lda $22
 clc
 adc #2
 sta VARTAB
 sta ARYTAB
 sta STREND
 lda $23
 adc #0
 sta VARTAB+1
 sta ARYTAB+1
 sta STREND+1
 rts
;finishop: point TXTPTR at the program start again (consistent editor state).
finishop
 jmp RUNC

;==================== reference scanner + in-place resize ====================
; Ported verbatim from mdbasic.asm renumer pass 2. Walks every line; on each line-
; number-reference token it evaluates the number, maps it (mapnum), and overwrites
; the ASCII digits in place, growing/shrinking the program with inc2d/dec2d.
;
; refpass (blkmode=0) walks the whole program to end-of-link ($0000), as renum/
; move need (every reference anywhere may need retargeting). refpass_blk
; (blkmode=1) instead starts at blkstart and stops after exactly scount lines --
; copy only wants to retarget references INSIDE the fresh duplicate, not scan the
; (unmodified, still valid) rest of the program. Both share every byte of the
; per-line body scan below; only rp_line's "next line / done" test differs.
refpass
 lda #0
 sta blkmode
 lda TXTTAB
 sec
 sbc #1
 sta TXTPTR
 lda TXTTAB+1
 sbc #0
 sta TXTPTR+1
 jmp rp_line

refpass_blk
 lda #1
 sta blkmode
 lda scount
 sta blkcnt
 lda scount+1
 sta blkcnt+1
 lda blkstart
 sec
 sbc #1
 sta TXTPTR
 lda blkstart+1
 sbc #0
 sta TXTPTR+1
 ;fall through to rp_line

rp_line
 lda blkmode
 bne rp_line_blk
 jsr getchr           ;link lo
 jsr getchr           ;link hi
 bne rp_l1
 jmp rp_done          ;$0000 link -> end of program
rp_line_blk
 lda blkcnt
 ora blkcnt+1
 bne rp_line_blkd
 jmp rp_done          ;processed all scount lines of the block -> done
rp_line_blkd
 sec
 lda blkcnt
 sbc #1
 sta blkcnt
 lda blkcnt+1
 sbc #0
 sta blkcnt+1
 jsr getchr           ;link lo
 jsr getchr           ;link hi
rp_l1
 jsr getchr           ;num lo
 jsr getchr           ;num hi
nocrap
 jsr getchr
craper
 cmp #$22             ;quote?
 bne tokgo
crap
 jsr getchr
 beq rp_line          ;no closing quote -> end of line
 cmp #$22
 bne crap
 beq nocrap
tokgo
 tax
 beq rp_line          ;$00 -> end of line
 bpl nocrap           ;<$80 -> not a token
 ldx #7
chktok
 cmp gotok,x
 beq sav7a
 dex
 bpl chktok
 cmp #TOKEN_ERR
 bne nocrap
 jsr getchr
 cmp #"l"             ;ERRL ? (lowercase literal = PETSCII $4c, the stored 'L')
 bne craper
 jsr CHRGET
 cmp #TOKEN_EQUAL     ;ERRL= ?
 bne craper
sav7a
 lda TXTPTR
 sta OLDLIN
 lda TXTPTR+1
 sta OLDLIN+1
 jsr CHRGET
 bcs craper           ;not a digit -> not a line-number reference
 jsr evalnum          ;ASCII digits -> LINNUM
 jsr mapnum           ;LINNUM -> new-number ASCII in BAD
 lda OLDLIN+1
 sta TXTPTR+1
 lda OLDLIN
 sta TXTPTR
 ldy #0
 ldx #0
numchr
 lda BAD,x
 cmp #"0"
 bcc less0
 pha
 jsr CHRGET
 bcc skp2d
 jsr inc2d
skp2d
 pla
 ldy #0
 sta (TXTPTR),y
 inx
 bne numchr
less0
 jsr CHRGET
 bcs workdone
dec2d
 jsr clrflg
 dec XSAV
work
 ldy COUNT
 iny
 lda ($22),y
 ldy XSAV
 iny
 sta ($22),y
 jsr pntreq
 beq crush1
 inc $22
 bne work
 inc $23
 bne work
 jsr bufer
crush1
 lda VARTAB
 bne ne2d
 dec VARTAB+1
ne2d
 dec VARTAB
 jsr CHRGOT
 bcc dec2d
workdone
 cmp #","
 beq sav7a
 jmp craper
rp_done
 rts

inc2d
 jsr clrflg
 inc XSAV
 jsr bufer
 inc VARTAB
 bne gbwyc
 inc VARTAB+1
gbwyc
 rts
pne2
 lda $24
 bne ne24
 dec $25
ne24
 dec $24
bufer
 ldy COUNT
 lda ($24),y
 ldy XSAV
 sta ($24),y
 jsr pntreq
 bne pne2
 rts
pntreq
 lda $22
 cmp $24
 bne gbhah
 lda $23
 cmp $25
gbhah
 rts
clrflg
 lda TXTPTR
 sta $22
 lda TXTPTR+1
 sta $23
 lda VARTAB
 sta $24
 lda VARTAB+1
 sta $25
 ldy #0
 sty COUNT
 sty XSAV
 rts

;getchr: advance TXTPTR one byte and read it (mdbasic getchr).
getchr
 ldy #0
 inc TXTPTR
 bne gc_x
 inc TXTPTR+1
gc_x
 lda (TXTPTR),y
 rts

;evalnum: evaluate the line-number literal at TXTPTR into LINNUM (ROM in).
evalnum
 jsr FRMNUM
 jmp GETADR

;8 tokens that reference a line number (GOTO GOSUB RETURN THEN ELSE RESUME RUN RESTORE)
gotok
 .byte $89, $8d, $8e, $a7, $cc, $e8, $8a, $8c

;==================== text ====================
;text is authored lowercase so tmpx emits PETSCII $41-$5a (unshifted uppercase),
;which CHROUT/the screen render as real uppercase letters (not shifted graphics).
hdrtxt
.ifdef TOOL_RENUM
 .text "mdbasic renumber"
 .byte $0d
 .text "r [inc] [start] [end] [dest]"
.endif
.ifdef TOOL_MOVE
 .text "mdbasic move"
 .byte $0d
 .text "m start end dest"
.endif
.ifdef TOOL_COPY
 .text "mdbasic copy"
 .byte $0d
 .text "c start end dest"
.endif
 .byte $0d
 .text "run/stop = exit"
 .byte $0d, $0d, $00
sOK        .null "ok"
sSYN       .null "?syntax"
sRANGE     .null "?>63999"
sCOLL      .null "?collision"
sNONE      .null "no lines"
sENDST     .null "?end<start"
restab
 .word sOK, sSYN, sRANGE, sCOLL, sNONE, sENDST

;==================== variables ====================
op        .byte 0
inc16     .word 0
lo16      .word 0
end16     .word 0
base16    .word 0
mstart    .word 0
mend      .word 0
mdest     .word 0
newmin    .word 0
newmax    .word 0
minsrc    .word 0
maxsrc    .word 0
scount    .word 0
cnt       .word 0
lastnew   .word 0
beforeN   .word 0
afterN    .word 0
haveb     .byte 0
havea     .byte 0
mfound    .byte 0
curnum    .word 0
rlo       .word 0
rhi       .word 0
t16       .word 0
numbuf    .word 0
tmpm      .word 0
tmpn      .word 0
P0        .word 0
P1        .word 0
INSp      .word 0
swA       .word 0
swB       .word 0
swC       .word 0
rstart    .word 0
rend      .word 0
blocklen  .word 0
srcpost   .word 0
blkstart  .word 0
blkcnt    .word 0
blkmode   .byte 0
resultcode .byte 0
bufi      .byte 0
sav01     .byte 0
savnmi    .word 0
inbuf     .repeat 40, 0
