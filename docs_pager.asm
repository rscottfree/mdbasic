; ***MDBASIC docs pager***
; Full-screen viewer for the manual bundled in the Magic Desk doc banks.
;
; Stored in cart bank 3 at $8000; the RESTORE handler copies it to $c000 and
; JSRs it (see docs-pager design). Assembled for $c000 (run location).
;
;   on entry: $02 = topic token (always 0 from docs_help.asm); bank 3 paged in
;             only long enough for the hook's code copy.
;   on exit:  cart paged out, NMI/cursor/$01 restored, screen cleared, RTS.
;
; Pager opens on a SEARCH page (mode=0). The user types to filter the keyword
; grid, presses ENTER to open a help page (mode=1), and F2 to toggle between
; the two views. F3/F5 navigate to adjacent topics in doc view.
;
; Discipline: whenever a cart bank is paged in ($8000-$9fff = doc ROM, which
; shadows MDBASIC's own image), interrupts are masked (SEI) and a safe NMI stub
; neutralises RESTORE. Cart is paged out + CLI whenever we wait for a key.

; --- build constants (must match tools/build_docs.py) ---
INDEX_BANK   = 3
DATA_BANK0   = 4
LINESPERBANK = 204
COLS         = 40
ROWS         = 25
NAMELEN      = 19     ;display name length (C64 screen codes, space-padded)
IXSTRIDE     = 24     ;index entry bytes: token(1)+start(2)+count(2)+name(19)
IXNAME       = 5      ;offset of display name in entry
NCOLS        = 2      ;search grid columns
COLW         = 20     ;column stride (NAMELEN=19 name + 1-space divider)
GRIDTOP      = 2      ;first scrolling grid row (rows 0-1 fixed: search + rule)
VISROWS      = 20     ;visible grid rows (rows 2-21; rows 22-24 fixed: rule+legend)

; --- zero page / kernal ---
TOPICTOK = $02        ;topic token passed by the RESTORE handler (unused zp)
SRCP     = $fb        ;source pointer (cart read)    -- graphics temp, free here
SCRP     = $fd        ;screen dest pointer           -- graphics temp, free here
R6510    = $01
BLNSW    = $cc
BLNCT    = $cd        ;cursor blink countdown (20 = one full period)
GDCHAR   = $ce        ;char displayed under the cursor (kernal)
BLNON    = $cf        ;cursor blink phase ($00=block on screen, $ff=char shown)
PNT      = $d1        ;pointer to the current screen line (lo/hi)
PNTR     = $d3        ;cursor column on the current line
TBLX     = $d6        ;cursor physical row
COLOR    = $0286
HIBASE   = $0288      ;top page of screen memory for kernal prints
NMIVEC   = $0318
KEYLOG   = $028f      ;keyboard decode-table setup vector (MDBASIC hooks this)
STDKEYLOG = $eb48     ;kernal's standard decode-table setup (no func-key strings)
SCREEN   = $0400
SPENA    = $d015      ;sprite enable register
SCROLY   = $d011      ;VIC control register 1
SCROLX   = $d016      ;VIC control register 2
VMCSB    = $d018      ;VIC video matrix + char base
EXTCOL   = $d020      ;border color
BGCOL0   = $d021      ;background color 0
U64SPEED = $d031      ;Ultimate 64 turbo register: bits 0-3 = CPU speed index (15=max)
CI2PRA   = $dd00      ;CIA2 port A: VIC bank select
C2DDRA   = $dd02      ;CIA2 port A data direction
COLRAM   = $d800
CART     = $de00
GETIN    = $ffe4
CLRSCR   = $e544      ;kernal clear screen
SCRBUF   = $cc00      ;1K snapshot of screen RAM ($0400-$07ff), saved on entry and
                      ;restored on exit. Free scratch above the $c000 pager image
                      ;and below I/O; outside the copied image so it costs no
                      ;cart/PAGER_MAX budget.

; index layout in bank 3 at $8c00 (3K reserve $8c00-$97ff; handler at $9800).
; sits just above the pager code copied to $c000, below the RESTORE handler.
IXMAGIC  = $8c00      ;'MDIX'
IXCOUNT  = $8c04      ;u16 topic count
IXTOTAL  = $8c06      ;u16 total lines
IXENTRY  = $8c08      ;24-byte entries: {token,startlo,starthi,cntlo,cnthi,name[19]}

*=$c000

;==================== entry ====================
entry
 lda R6510
 sta sav01
 lda #$37            ;BASIC+KERNAL+I/O in, LORAM=1 so cart shows at $8000
 sta R6510
 lda BLNSW
 sta savbln
 lda #1
 sta BLNSW           ;disable cursor blink for the session
 lda NMIVEC
 sta savnmi
 lda NMIVEC+1
 sta savnmi+1
 lda #<nmistub
 sta NMIVEC
 lda #>nmistub
 sta NMIVEC+1
 lda KEYLOG          ;MDBASIC redirects function keys to its KEY strings; point
 sta savkey          ;the decode-table vector back at the kernal standard so the
 lda KEYLOG+1        ;pager sees raw F1-F8 codes on a single press, not held
 sta savkey+1
 lda #<STDKEYLOG
 sta KEYLOG
 lda #>STDKEYLOG
 sta KEYLOG+1
 sei
 lda #INDEX_BANK
 sta CART
 jsr scanindex       ;sets totlines; topline=0 (TOPICTOK always 0 from handler)
 lda #$80
 sta CART
 cli
 lda EXTCOL
 sta savbdr
 lda BGCOL0
 sta savbg
 lda COLOR
 sta savfg
 lda VMCSB
 sta savvmc
 lda U64SPEED        ;Ultimate 64: save the current turbo speed bits, then run flat
 sta savturbo        ;out (harmless on stock C64/VICE - $d031 reads $ff, drops writes)
 ora #$0f            ;speed index 15 = max turbo (48/64 MHz); badline bit 7 preserved
 sta U64SPEED
 lda #0
 sta EXTCOL          ;black border
 sta BGCOL0          ;black background
 lda #14
 sta COLOR           ;light blue foreground
 lda #0
 sta SPENA           ;all sprites off
 jsr savescreen      ;snapshot screen RAM + cursor pos so exit can restore them
 jsr savecolor       ;snapshot color RAM (packed 2:1) before fillcolor overwrites it
 jsr forcetext       ;standard text screen at $0400 (in case graphics was on)
 jsr fillcolor
 ;fall into mainloop (mode=0 = search page, set by variable initialiser)

;==================== main loop ====================
mainloop
 lda mode
 bne docview         ;mode != 0 -> doc view (falls through below)
 jmp ml_search       ;mode == 0 -> search page (out of branch range)

;==================== doc view ====================
; Plain line-at-a-time scrolling. Interrupts stay ON and EVERY key comes from
; GETIN -- the kernal IRQ does the keyscan, debounce, and auto-repeat for us. This
; is the same path the BASIC cursor uses, which is why it stops the instant you let
; go on real hardware, VICE, and the U64 alike. CRSR up/down move topline by one
; line and redraw the page (held -> the kernal auto-repeats -> continuous scroll
; that stops on release); every other key jumps directly. (A pixel-smooth scroll
; was attempted twice and reverted -- see docs/smooth-scroll-attempt.md.)
docview
 jsr render          ;draw the page from topline (CLIs on exit)
dv_wait
 jsr GETIN
 beq dv_wait
 cmp #$11            ;CRSR down -> scroll forward one line
 beq dv_down
 cmp #$91            ;CRSR up   -> scroll back one line
 beq dv_up
 cmp #$03            ;RUN/STOP  -> exit
 beq dv_exit
 cmp #$89            ;F2        -> search page
 beq dv_f2
 cmp #$13            ;HOME      -> top of doc
 beq dv_top
 cmp #$88            ;F7        -> page down
 beq dv_pgdn
 cmp #$20            ;SPACE     -> page down
 beq dv_pgdn
 cmp #$85            ;F1        -> page up
 beq dv_pgup
 cmp #$86            ;F3        -> previous topic
 beq dv_prevtop
 cmp #$87            ;F5        -> next topic
 beq dv_nexttop
 jmp dv_wait

dv_down
 jsr linedown
 jmp docview
dv_up
 jsr lineup
 jmp docview

dv_exit jmp exit     ;trampoline: exit is out of direct branch range

dv_f2
 lda #0
 sta mode
 jmp mainloop
dv_top
 lda #0
 sta topline
 sta topline+1
 jmp docview
dv_pgdn
 ldx #ROWS-1
dpd1
 jsr linedown
 dex
 bne dpd1
 jmp docview
dv_pgup
 ldx #ROWS-1
dpu1
 jsr lineup
 dex
 bne dpu1
 jmp docview
dv_prevtop
 jsr prevtopic
 jmp docview
dv_nexttop
 jsr nexttopic
 jmp docview

;==================== search page ====================
ml_search
 jsr render_search   ;draw grid; sets numvis; render_search rts -> falls into poll
input_search
 jsr GETIN
 beq input_search
 cmp #$03            ;RUN/STOP -> exit
 beq is_xit
 cmp #$0d            ;RETURN -> open selected entry
 beq is_seljmp
 cmp #$89            ;F2 -> doc view
 beq is_f2jmp
 cmp #$1d            ;CRSR right -> next entry (within row)
 beq is_next
 cmp #$9d            ;CRSR left -> prev entry (within row)
 beq is_prevjmp
 cmp #$11            ;CRSR down -> down a row (same column)
 beq is_downjmp
 cmp #$91            ;CRSR up -> up a row (same column)
 beq is_upjmp
 cmp #$85            ;F1 -> page up the results list
 beq is_pgupjmp
 cmp #$88            ;F7 -> page down the results list
 beq is_pgdnjmp
 cmp #$14            ;DEL -> backspace in filter
 beq is_del
 cmp #$93            ;SHIFT+CLR/HOME -> clear filter (undocumented)
 beq is_clr
 ;--- printable char: add to filter ---
 cmp #$21
 bcc input_search    ;PETSCII < $21 (control chars / space) -> ignore
 cmp #$80
 bcs input_search    ;PETSCII >= $80 (unhandled special keys) -> ignore
 jsr petscr          ;convert PETSCII to C64 screen code
 ldx filtlen
 cpx #NAMELEN
 bcs input_search    ;filter full -> ignore
 sta filtbuf,x
 inc filtlen
 lda #0
 sta selvis
 jmp search_upd

is_xit   jmp exit   ;trampolines: targets are out of direct branch range
is_seljmp  jmp is_select
is_prevjmp jmp is_prev
is_f2jmp   jmp is_f2
is_downjmp jmp is_down
is_upjmp   jmp is_up
is_pgupjmp jmp is_pgup
is_pgdnjmp jmp is_pgdn

is_del
 lda filtlen
 beq input_search
 dec filtlen
 lda #0
 sta selvis
 jmp search_upd

is_clr
 lda filtlen
 beq input_search    ;already empty -> nothing to redraw
 lda #0
 sta filtlen
 sta selvis
 jmp search_upd

; Selection moves change selvis and jump to search_upd, which redraws the grid in
; place (draw_grid: re-counts matches, scrolls to keep the selection visible,
; inverts the selected cell) without clearing the page -- so there is no flash.
; selvis wraps within numvis. CRSR left/right step by one entry; CRSR up/down step
; by a row (NCOLS entries), same column. The grid is 2 columns; a row = NCOLS=2.
is_nop
 jmp input_search

search_upd             ;redraw grid in place, then keep polling
 jsr draw_grid
 jmp input_search

is_next
 lda numvis
 beq is_nop
 inc selvis
 lda selvis
 cmp numvis
 bcc isn_done
 lda #0
 sta selvis
isn_done
 jmp search_upd

is_prev
 lda numvis
 beq is_nop
 lda selvis
 bne isp_dec
 lda numvis          ;at 0 -> wrap to last entry
 sec
 sbc #1
 sta selvis
 jmp search_upd
isp_dec
 dec selvis
 jmp search_upd

is_down
 lda numvis
 beq is_nop
 lda selvis
 clc
 adc #NCOLS
 cmp numvis
 bcc isd_ok          ;next row exists
 lda selvis
 and #$01            ;wrap to top of this column (NCOLS=2 -> column = bit 0)
isd_ok
 sta selvis
 jmp search_upd

is_up
 lda numvis
 beq is_nop
 lda selvis
 sec
 sbc #NCOLS
 bcs isu_ok          ;prev row exists (selvis >= NCOLS)
 ;top row: wrap to the bottom entry of this column (column = selvis < NCOLS)
 lda numvis
 sec
 sbc #1              ;last entry index
 and #$fe            ;base of its row (round down to multiple of NCOLS=2)
 clc
 adc selvis          ;base + column
 cmp numvis
 bcc isu_ok          ;column has an entry on the bottom row
 sbc #NCOLS          ;otherwise step up one row (carry set from cmp)
isu_ok
 sta selvis
 jmp search_upd

is_f2
 lda #1
 sta mode
 jmp mainloop

is_select
 jsr find_selected   ;sets topline + mode=1 if any match found
 jmp mainloop

; F1/F7 page the results grid by a full window (VISROWS rows). Rather than fight
; ensure_visible (which only ever scrolls one window-edge at a time toward the
; selection) we move scrolltop directly and park selvis on the new window's
; top-left entry, so selrow == scrolltop and ensure_visible leaves it put. numvis
; reflects the current filter, so the clamp tracks the live result count.
is_pgdn
 lda numvis
 clc
 adc #1
 lsr                 ;A = numrows = ceil(numvis/NCOLS)
 sec
 sbc #VISROWS        ;maxscroll = numrows - VISROWS ...
 bcs pd_clamp
 lda #0              ;... or 0 if the grid is shorter than the window
pd_clamp
 sta maxscr
 lda scrolltop
 clc
 adc #VISROWS        ;newtop = scrolltop + VISROWS
 cmp maxscr
 bcc pd_set          ;newtop < maxscroll -> use it
 lda maxscr          ;else clamp to the last page
pd_set
 sta scrolltop
 asl                 ;selvis = scrolltop*NCOLS (top-left of the window)
 sta selvis
 jmp search_upd

is_pgup
 lda scrolltop
 sec
 sbc #VISROWS        ;newtop = scrolltop - VISROWS
 bcs pu_set
 lda #0              ;clamp to the first row
pu_set
 sta scrolltop
 asl                 ;selvis = scrolltop*NCOLS (top-left of the window)
 sta selvis
 jmp search_upd

;==================== exit ====================
exit
 lda savnmi
 sta NMIVEC
 lda savnmi+1
 sta NMIVEC+1
 lda savkey          ;restore MDBASIC's function-key decode hook
 sta KEYLOG
 lda savkey+1
 sta KEYLOG+1
 lda #$80
 sta CART            ;ensure cart paged out
 jsr restorescreen   ;put the saved screen RAM + cursor position back (no CLRSCR,
                     ;so the editor's line pointer/cursor state is undisturbed)
 jsr restorecolor    ;unpack the saved color RAM back over fillcolor's solid fill
 lda savbln
 sta BLNSW           ;resume the prior blink-enable state
 lda #$ff
 sta BLNON           ;char-shown phase: the resumed kernal IRQ draws a fresh
                     ;cursor block, leaving no stale block artifact
 lda #1
 sta BLNCT           ;blink almost immediately
 lda savbdr
 sta EXTCOL
 lda savbg
 sta BGCOL0
 lda savfg
 sta COLOR
 lda savvmc
 sta VMCSB
 lda savturbo
 sta U64SPEED        ;restore the Ultimate 64 turbo speed bits
 lda sav01
 sta R6510
 rts

nmistub
 rti                 ;neutralise RESTORE while a cart bank is paged in

;==================== shared index-scan helpers ====================
; advsrc: advance SRCP to the next index entry (+= IXSTRIDE).
advsrc
 lda SRCP
 clc
 adc #IXSTRIDE
 sta SRCP
 bcc adv_nc
 inc SRCP+1
adv_nc
 rts

; scan_begin: mask IRQs, page in the index bank, point SRCP at the first entry,
; and load rscnt = numtop = IXCOUNT (low byte; max 71 topics < 256). The doc-view
; key dispatch never lowers R6510 from $37, but it is re-asserted here to match
; the rest of the pager's cart-paging discipline.
scan_begin
 sei
 lda #$37
 sta R6510
 lda #INDEX_BANK
 sta CART
 lda #<IXENTRY
 sta SRCP
 lda #>IXENTRY
 sta SRCP+1
 lda IXCOUNT
 sta rscnt
 sta numtop
 rts

; pageout: page the cart out and re-enable IRQs (the common scanner epilogue).
pageout
 lda #$80
 sta CART
 cli
 rts

;==================== scroll helpers ====================
; linedown: topline++ clamped to totlines-1
linedown
 lda topline+1
 cmp totlines+1
 bcc ld_ok
 bne ld_no
 lda topline
 cmp totlines       ;topline < totlines ?
 bcs ld_clamp
ld_ok
 inc topline
 bne ld_done
 inc topline+1
ld_done
 lda topline+1
 cmp totlines+1
 bcc ld_no
 bne ld_clamp
 lda topline
 cmp totlines
 bcc ld_no
ld_clamp
 lda totlines
 sec
 sbc #1
 sta topline
 lda totlines+1
 sbc #0
 sta topline+1
ld_no
 rts

; lineup: topline-- clamped to 0
lineup
 lda topline
 ora topline+1
 beq lu_no
 lda topline
 bne lu_dec
 dec topline+1
lu_dec
 dec topline
lu_no
 rts

;==================== index scan ====================
; out: topline=0, totlines from IXTOTAL. The handler always passes TOPICTOK=0
; (open at the start), so the old topic-search loop here was unreachable and is
; gone; restore it from git if a caller ever opens the pager on a specific topic.
; called with cart bank 3 paged in under SEI.
scanindex
 lda #0
 sta topline
 sta topline+1
 lda IXTOTAL
 sta totlines
 lda IXTOTAL+1
 sta totlines+1
 rts

;==================== render (doc page) ====================
; draw ROWS-1 doc lines starting at topline, then a reverse-video status bar of
; the doc-view key bindings on the last row. cart paged in under sei.
render
 jsr divmod
 jsr srcfromwr
 lda topline
 sta lineidx
 lda topline+1
 sta lineidx+1
 lda #<SCREEN
 sta SCRP
 lda #>SCREEN
 sta SCRP+1
 sei
 lda wbank          ;R6510 stays $37 for the whole session; no need to re-set it
 sta CART
 ldx #0
 stx row
rowloop
 lda lineidx+1
 cmp totlines+1
 bcc rl_text
 bne rl_blank
 lda lineidx
 cmp totlines
 bcc rl_text
rl_blank
 ldy #COLS-1
 lda #$20
rl_bl
 sta (SCRP),y
 dey
 bpl rl_bl
 jmp rl_adv
rl_text
 ldy #COLS-1
rl_cp
 lda (SRCP),y
 sta (SCRP),y
 dey
 bpl rl_cp
rl_adv
 lda SCRP
 clc
 adc #COLS
 sta SCRP
 bcc rl_s1
 inc SCRP+1
rl_s1
 lda SRCP
 clc
 adc #COLS
 sta SRCP
 bcc rl_s2
 inc SRCP+1
rl_s2
 inc lineidx
 bne rl_s3
 inc lineidx+1
rl_s3
 inc wr
 lda wr
 cmp #LINESPERBANK
 bne rl_next
 lda #0
 sta wr
 inc wbank
 lda wbank
 sta CART
 lda #$00
 sta SRCP
 lda #$80
 sta SRCP+1
rl_next
 inc row
 lda row
 cmp #ROWS-1         ;leave the last row for the status bar
 bne rowloop
 lda #$80
 sta CART            ;cart out; the status data lives in our $c000 image
 ;--- reverse-video status bar of doc-view keys on the last row ---
 lda #<docleg
 sta SRCP
 lda #>docleg
 sta SRCP+1
 lda #<(SCREEN+((ROWS-1)*COLS))
 sta SCRP
 lda #>(SCREEN+((ROWS-1)*COLS))
 sta SCRP+1
 jsr drawstatus
 cli
 rts

; SRCP = $8000 + wr*40   (wr in 0..203)
srcfromwr
 lda wr
 sta mlo
 lda #0
 sta mhi
 asl mlo
 rol mhi            ;*2
 asl mlo
 rol mhi            ;*4
 lda mlo
 clc
 adc wr
 sta mlo
 lda mhi
 adc #0
 sta mhi            ;*5
 asl mlo
 rol mhi
 asl mlo
 rol mhi
 asl mlo
 rol mhi            ;*40
 lda mlo
 sta SRCP
 lda mhi
 clc
 adc #$80           ;base $8000
 sta SRCP+1
 rts

; divmod: topline / 204 -> wbank = DATA_BANK0 + quotient, wr = remainder
divmod
 lda topline
 sta wr
 lda topline+1
 sta wrh
 lda #0
 sta quot
dm_loop
 lda wrh
 bne dm_sub
 lda wr
 cmp #LINESPERBANK
 bcc dm_done
dm_sub
 lda wr
 sec
 sbc #LINESPERBANK
 sta wr
 lda wrh
 sbc #0
 sta wrh
 inc quot
 jmp dm_loop
dm_done
 lda quot
 clc
 adc #DATA_BANK0
 sta wbank
 rts

;==================== color fill ====================
fillcolor
 lda COLOR
 ldx #0
fc1
 sta COLRAM,x
 sta COLRAM+$100,x
 sta COLRAM+$200,x
 sta COLRAM+$2e8,x
 inx
 bne fc1
 rts

;==================== screen snapshot / restore ====================
; savescreen: stash screen RAM ($0400-$07ff) into SCRBUF and remember the cursor
; position, so exit can put the user's screen back. The cursor is de-blinked
; first: if a cursor block is currently on screen (BLNON=$00), the true char
; under it (GDCHAR) is written back to the cursor cell so the snapshot doesn't
; capture the inverted block as a stale artifact.
savescreen
 lda BLNON
 bne ss_pos          ;char shown (no block) -> cell already holds the real char
 ldy PNTR            ;block on screen -> restore the true char to the cursor cell
 lda GDCHAR
 sta (PNT),y         ;cell = (current line)+column
ss_pos
 lda PNTR
 sta savd3
 lda TBLX
 sta savd6
 ldx #0
ss_cp
 lda SCREEN,x
 sta SCRBUF,x
 lda SCREEN+$100,x
 sta SCRBUF+$100,x
 lda SCREEN+$200,x
 sta SCRBUF+$200,x
 lda SCREEN+$300,x
 sta SCRBUF+$300,x
 inx
 bne ss_cp
 rts

; restorescreen: copy the saved screen RAM back to $0400 and restore the cursor
; row/column. PNT (line pointer) was never disturbed by the pager, so it still
; matches the restored row/column.
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
 lda savd3
 sta PNTR
 lda savd6
 sta TBLX
 rts

;==================== color snapshot / restore ====================
; Only the low nybble of each color-RAM cell is meaningful, so the 1000 cells
; ($d800-$dbe7) pack 2:1 into the 500-byte COLBUF: even cell -> high nybble,
; odd cell -> low nybble. This keeps the user's per-character colors across a
; docs session without spending a second 1K buffer. I/O is paged in here, so
; the color RAM is directly addressable. SRCP/SCRP are free at entry/exit.
savecolor
 lda #<COLRAM
 sta SRCP
 lda #>COLRAM
 sta SRCP+1
 lda #<COLBUF
 sta SCRP
 lda #>COLBUF
 sta SCRP+1
sc_lp
 ldy #0
 lda (SRCP),y        ;even cell -> high nybble
 asl
 asl
 asl
 asl
 sta pktmp
 iny
 lda (SRCP),y        ;odd cell -> low nybble
 and #$0f
 ora pktmp
 dey
 sta (SCRP),y
 jsr advcol          ;SRCP += 2, SCRP += 1
 bne sc_lp
 rts

restorecolor
 lda #<COLRAM
 sta SRCP
 lda #>COLRAM
 sta SRCP+1
 lda #<COLBUF
 sta SCRP
 lda #>COLBUF
 sta SCRP+1
rc_lp
 ldy #0
 lda (SCRP),y        ;packed byte
 pha
 lsr                 ;high nybble -> even cell
 lsr
 lsr
 lsr
 sta (SRCP),y
 pla
 and #$0f            ;low nybble -> odd cell
 iny
 sta (SRCP),y
 jsr advcol
 bne rc_lp
 rts

; advcol: step the color pack/unpack pointers (SRCP += 2 over color RAM,
; SCRP += 1 over COLBUF) and return Z=0 until SRCP reaches the end of color RAM.
advcol
 lda SRCP
 clc
 adc #2
 sta SRCP
 bcc ac_dst
 inc SRCP+1
ac_dst
 inc SCRP
 bne ac_end
 inc SCRP+1
ac_end
 lda SRCP+1
 cmp #>(COLRAM+1000)
 bne ac_ne
 lda SRCP
 cmp #<(COLRAM+1000)
ac_ne
 rts

;==================== force standard text mode ====================
; Restore a normal 40x25 text display on VIC bank 0 with screen at $0400 and the
; ROM charset, in case the user had a bitmap/graphics screen up.
forcetext
 lda #%00011011     ;bitmap off, ECM off, 25 rows, display on
 sta SCROLY
 lda #%11001000     ;40 cols, multicolor off
 sta SCROLX
 lda CI2PRA
 ora #%00000011     ;VIC 16K bank 0 ($0000-$3fff)
 sta CI2PRA
 lda C2DDRA
 ora #%00000011     ;bits 0-1 output
 sta C2DDRA
 lda #%00010111     ;video matrix $0400, char dot data $1800 (ROM lowercase charset)
 sta VMCSB
 lda #$04
 sta HIBASE         ;kernal prints to $0400
 rts

;==================== petscr: PETSCII -> C64 screen code ====================
petscr
 cmp #$41
 bcc ps_lo
 cmp #$5b
 bcs ps_chk2
 rts                ;PETSCII A-Z -> screen codes $41-$5A unchanged (display uppercase)
ps_chk2
 cmp #$61
 bcc ps_lo
 cmp #$7b
 bcs ps_lo
 sec
 sbc #$60           ;PETSCII a-z -> screen codes $01-$1A (display lowercase)
 rts
ps_lo
 cmp #$20
 bcs ps_ok
 lda #$20           ;non-printable -> space
ps_ok
 rts

;==================== render_search ====================
; Paint the static chrome of the search page, then fall into draw_grid for the
; filter line + keyword grid. This is the ONLY path that clears the screen, so it
; runs just on view entry (initial open, or F2 back from the doc view) -- never
; per keystroke, where the clear would flash the whole page. Layout:
;   row 0        "SEARCH: "+filter            (filter drawn by draw_grid)
;   row 1        horizontal rule
;   rows 2..21   2-column keyword grid (draw_grid)
;   row 22       horizontal rule
;   rows 23-24   controls legend
render_search
 ;--- clear all 1000 screen bytes (view entry only) ---
 lda #$20
 ldx #0
rsc_cl1
 sta SCREEN,x
 sta SCREEN+$100,x
 sta SCREEN+$200,x
 inx
 bne rsc_cl1
 ldx #0
rsc_cl2
 sta SCREEN+$300,x
 inx
 cpx #$e8           ;232 = 1000-768
 bne rsc_cl2
 ;--- "SEARCH: " label on row 0 ---
 ldx #0
rsc_hdr
 lda srchmsg,x
 sta SCREEN,x
 inx
 cpx #8
 bne rsc_hdr
 ;--- rule under the search box (row 1) ---
 lda #1
 jsr scrp_row
 jsr fillrule
 ;--- rule above the legend (row 22) ---
 lda #22
 jsr scrp_row
 jsr fillrule
 ;--- controls legend on rows 23-24 ---
 lda #<leg1
 sta SRCP
 lda #>leg1
 sta SRCP+1
 lda #<(SCREEN+(23*COLS))
 sta SCRP
 lda #>(SCREEN+(23*COLS))
 sta SCRP+1
 jsr drawleg
 lda #<leg2
 sta SRCP
 lda #>leg2
 sta SRCP+1
 lda #<(SCREEN+(24*COLS))
 sta SCRP
 lda #>(SCREEN+(24*COLS))
 sta SCRP+1
 jsr drawleg
 ;fall into draw_grid for the filter line + keyword grid

;==================== draw_grid ====================
; Redraw the filter line (row 0) and the keyword grid (rows 2..21) IN PLACE --
; no screen clear -- so unchanged cells get identical bytes and the page never
; blanks. This is what runs on every keystroke (search_upd). The grid is a single
; list of filter-matching entries in row-major order: entry i sits at logical row
; i/NCOLS, column i%NCOLS; scrolltop is the first logical row shown. blank_tail
; wipes any cells past the last match so a shrinking filter leaves nothing stale.
; Sets numvis.
draw_grid
 jsr ensure_visible ;scroll so the selection sits within rows 2..21
 ;--- filter text on row 0 after the prompt, padded with spaces to NAMELEN ---
 ldx #0
dg_fb
 cpx #NAMELEN
 beq dg_grid
 cpx filtlen
 bcc dg_fbchar
 lda #$20           ;past the filter -> blank (clears deleted chars)
 jmp dg_fbput
dg_fbchar
 lda filtbuf,x
dg_fbput
 sta SCREEN+8,x
 inx
 bne dg_fb          ;always (x < NAMELEN=19)
dg_grid
 ;--- scan index under SEI, drawing matching entries in place ---
 lda #0
 sta numvis         ;doubles as the running visible-entry index during the scan
 jsr scan_begin
dg_lp
 lda rscnt
 beq dg_done
 jsr filtmatch      ;C=1 match; namebuf filled either way
 bcc dg_skip
 ;--- match: logical row = numvis/NCOLS, column = numvis%NCOLS ---
 lda numvis
 lsr                ;A = logical row, C = column (bit 0, NCOLS=2)
 sta gr_row
 lda #0
 rol                ;A = column (carry rolled in)
 sta gr_col
 ;--- visible? scrolltop <= gr_row < scrolltop+VISROWS ---
 lda gr_row
 cmp scrolltop
 bcc dg_nodraw      ;above the window
 sec
 sbc scrolltop      ;rr = gr_row - scrolltop
 cmp #VISROWS
 bcs dg_nodraw      ;below the window
 jsr cellscrp       ;A=rr, gr_col set -> SCRP = cell address
 ;--- invert the selected entry ---
 lda numvis
 cmp selvis
 bne dg_write
 ldx #0
dg_inv
 lda namebuf,x
 ora #$80
 sta namebuf,x
 inx
 cpx #NAMELEN
 bne dg_inv
dg_write
 ldy #0
dg_wrt
 lda namebuf,y
 sta (SCRP),y
 iny
 cpy #NAMELEN
 bne dg_wrt
dg_nodraw
 inc numvis
dg_skip
 jsr advsrc
 dec rscnt
 bne dg_lp
dg_done
 jsr blank_tail     ;wipe visible cells past the last match (cart still paged)
 jmp pageout

;==================== blank_tail ====================
; Space-fill the visible grid cells from position numvis to the end of the window
; (positions numvis..(scrolltop+VISROWS)*NCOLS - 1), clearing names left over from
; a wider match set. Called from draw_grid with cart bank 3 still paged in.
blank_tail
 lda scrolltop
 clc
 adc #VISROWS
 asl                ;*NCOLS (=2): one past the last visible position
 sta bp_end
 lda numvis
 sta bp
bt_lp
 lda bp
 cmp bp_end
 bcs bt_done
 lsr                ;gr_row = bp/NCOLS, C = column
 sta gr_row
 lda #0
 rol
 sta gr_col
 lda gr_row
 sec
 sbc scrolltop      ;rr
 jsr cellscrp
 ldy #NAMELEN-1
 lda #$20
bt_wr
 sta (SCRP),y
 dey
 bpl bt_wr
 inc bp
 jmp bt_lp
bt_done
 rts

;==================== cellscrp ====================
; SCRP = screen address of a grid cell. In: A = rr (logical row - scrolltop),
; gr_col = column. Clobbers mlo/mhi/dtmp (via scrp_row).
cellscrp
 clc
 adc #GRIDTOP       ;screen row = GRIDTOP + rr
 jsr scrp_row       ;SCRP = SCREEN + screenrow*40
 lda gr_col
 beq cs_done        ;column 0 -> no offset
 lda SCRP
 clc
 adc #COLW          ;column 1 -> + COLW
 sta SCRP
 bcc cs_done
 inc SCRP+1
cs_done
 rts

;==================== ensure_visible ====================
; Scroll the grid so the selected entry's logical row (selvis/NCOLS) is within
; the VISROWS-row window. scrolltop only changes when the selection leaves the
; window, so single-step cursor moves scroll exactly one line at a time.
ensure_visible
 lda selvis
 lsr                ;selrow = selvis / NCOLS
 sta selrow
 cmp scrolltop
 bcc ev_above       ;selrow < scrolltop -> scroll up to it
 sec
 sbc scrolltop      ;selrow - scrolltop
 cmp #VISROWS
 bcc ev_done        ;already visible
 lda selrow         ;below window -> put selrow on the last visible row
 sec
 sbc #VISROWS-1
 sta scrolltop
 rts
ev_above
 lda selrow
 sta scrolltop
ev_done
 rts

;==================== scrp_row ====================
; SCRP = SCREEN + A*40   (A = screen row 0..24). Clobbers mlo/mhi/dtmp.
scrp_row
 sta mlo
 lda #0
 sta mhi
 asl mlo
 rol mhi            ;*2
 asl mlo
 rol mhi            ;*4
 asl mlo
 rol mhi            ;*8
 lda mlo
 sta dtmp
 lda mhi
 sta dtmp+1         ;save row*8
 asl mlo
 rol mhi            ;*16
 asl mlo
 rol mhi            ;*32
 lda mlo
 clc
 adc dtmp
 sta mlo
 lda mhi
 adc dtmp+1
 sta mhi            ;*40 = *32 + *8
 lda mlo
 clc
 adc #<SCREEN
 sta SCRP
 lda mhi
 adc #>SCREEN
 sta SCRP+1
 rts

;==================== fillrule ====================
; Fill the COLS bytes at (SCRP) with the horizontal-rule screen code ($40).
fillrule
 ldy #COLS-1
 lda #$40
fr_lp
 sta (SCRP),y
 dey
 bpl fr_lp
 rts

; drawleg: copy a 0-terminated string at (SRCP) to (SCRP), converting each char
; to a screen code. TMPx .text emits uppercase as shifted PETSCII ($c1-$da);
; map those to letter screen codes ($01-$1a). Digits/colon/space already match
; their screen codes, so pass them through. Used for the static controls legend.
drawleg
 ldy #0
dlg_lp
 lda (SRCP),y
 beq dlg_done
 cmp #$c1
 bcc dlg_put
 cmp #$db
 bcs dlg_put
 sec
 sbc #$c0           ;PETSCII A-Z -> screen codes 1-26
dlg_put
 sta (SCRP),y
 iny
 bne dlg_lp
dlg_done
 rts

;==================== drawstatus ====================
; Draw a full-width reverse-video status bar: the 0-terminated legend at (SRCP),
; converted to screen codes like drawleg and reverse-video'd, then padded to COLS
; with reverse-space ($a0), at the row starting at (SCRP).
drawstatus
 ldy #0
ds_lp
 lda (SRCP),y
 beq ds_pad         ;end of string -> pad the rest of the row
 cmp #$c1
 bcc ds_put
 cmp #$db
 bcs ds_put
 sec
 sbc #$c0           ;PETSCII A-Z -> screen codes 1-26
ds_put
 ora #$80           ;reverse video
 sta (SCRP),y
 iny
 cpy #COLS
 bne ds_lp
 rts
ds_pad
 lda #$a0           ;reverse-space
ds_padl
 sta (SCRP),y
 iny
 cpy #COLS
 bne ds_padl
 rts

;==================== filtmatch ====================
; in:  SRCP -> index entry; filtbuf/filtlen = active filter.
; out: C=1 if display name is a substring match of filter; namebuf filled.
; modifies: X, Y, namebuf, fmpos.
filtmatch
 ;--- copy 10-byte name from entry offset IXNAME to namebuf ---
 ldy #IXNAME
 ldx #0
fm_cpy
 lda (SRCP),y
 sta namebuf,x
 iny
 inx
 cpx #NAMELEN
 bne fm_cpy
 ;--- empty filter matches everything ---
 lda filtlen
 beq fm_yes
 ;--- substring search: try each start position ---
 lda #0
 sta fmpos
fm_outer
 lda fmpos
 clc
 adc filtlen
 cmp #NAMELEN+1     ;fmpos+filtlen > NAMELEN -> exhausted
 bcs fm_no
 ldy fmpos
 ldx #0
fm_inner
 cpx filtlen
 beq fm_yes
 lda namebuf,y
 cmp filtbuf,x
 bne fm_miss
 iny
 inx
 bne fm_inner       ;X < 11 here, never 0 after inx within filtlen<=10
fm_miss
 inc fmpos
 bne fm_outer       ;fmpos < 11, always non-zero after inc
fm_no
 clc
 rts
fm_yes
 sec
 rts

;==================== find_selected ====================
; Scan index for the selvis-th filter-matching entry. Set topline to its start
; line and mode=1 (doc view). No-op if no matches.
find_selected
 lda #0
 sta fscnt
 jsr scan_begin
fs_lp
 lda rscnt
 beq fs_done
 jsr filtmatch
 bcc fs_skip
 lda fscnt
 cmp selvis
 bne fs_notsel
 ;--- found the target entry ---
 ldy #1
 lda (SRCP),y
 sta topline
 ldy #2
 lda (SRCP),y
 sta topline+1
 jsr pageout
 lda #1
 sta mode
 rts
fs_notsel
 inc fscnt
fs_skip
 jsr advsrc
 dec rscnt
 bne fs_lp
fs_done
 jmp pageout

;==================== topic navigation (F3/F5) ====================
nexttopic
 lda #0
 sta topdir         ;0 = forward
 jmp dotopnav
prevtopic
 lda #1
 sta topdir         ;1 = backward
dotopnav
 jsr scan_begin     ;sets rscnt = numtop = IXCOUNT for the index arithmetic
tn_lp
 lda rscnt
 bne tn_not0
 jmp tn_done        ;rscnt=0: topline not found -> do nothing
tn_not0
 ;--- entry range: [start, start+count) ---
 ldy #1
 lda (SRCP),y
 sta mlo            ;start lo
 ldy #2
 lda (SRCP),y
 sta mhi            ;start hi
 ;end = start + count + 1: the +1 absorbs the one blank separator line that
 ;sits between this topic and the next (it is in no topic's indexed range, so
 ;without this F3/F5 do nothing when topline rests on it - one line above a
 ;title). The next topic starts at start+count+1, so the ranges never overlap.
 ldy #3
 lda (SRCP),y
 sec
 adc mlo
 sta dtmp           ;end lo
 ldy #4
 lda (SRCP),y
 adc mhi
 sta dtmp+1         ;end hi
 ;is topline >= start?
 lda topline+1
 cmp mhi
 bcc tn_next        ;topline.hi < start.hi -> before this entry
 bne tn_gteq        ;topline.hi > start.hi -> at or past start
 lda topline
 cmp mlo
 bcc tn_next        ;topline.lo < start.lo -> before
tn_gteq
 ;is topline < end?
 lda topline+1
 cmp dtmp+1
 bcc tn_inrange     ;topline.hi < end.hi -> in range
 bne tn_next        ;topline.hi > end.hi -> past this entry
 lda topline
 cmp dtmp
 bcs tn_next        ;topline.lo >= end.lo -> past
tn_inrange
 ;--- current entry found at index (numtop - rscnt) ---
 lda topdir
 beq tn_go_next
 ;--- prev: if scrolled past the topic's first line (mlo/mhi), F3 first
 ;    snaps back to that line; only when already at the top does it move
 ;    to the previous topic ---
 lda topline
 cmp mlo
 bne tn_curtop
 lda topline+1
 cmp mhi
 bne tn_curtop
 ;--- already at topic top: step to previous topic (can't from index 0) ---
 lda numtop
 sec
 sbc rscnt          ;current index (0-based from IXENTRY)
 beq tn_exit        ;already at first entry
 lda SRCP
 sec
 sbc #IXSTRIDE
 sta SRCP
 bcs tn_ps
 dec SRCP+1
tn_ps
 jmp tn_setline
tn_curtop
 lda mlo            ;snap to current topic's first line
 sta topline
 lda mhi
 sta topline+1
 jmp tn_exit
tn_go_next
 ;--- next: rscnt=1 means this is the last entry ---
 lda rscnt
 cmp #1
 beq tn_exit
 jsr advsrc
tn_setline
 ldy #1
 lda (SRCP),y
 sta topline
 ldy #2
 lda (SRCP),y
 sta topline+1
tn_exit
 jmp pageout
tn_next
 jsr advsrc
 dec rscnt
 beq tn_done        ;rscnt=0 -> loop done
 jmp tn_lp          ;otherwise scan next entry
tn_done
 jmp pageout

;==================== data ====================
; "SEARCH: " as C64 screen codes (S=$13 E=$05 A=$01 R=$12 C=$03 H=$08 :=$3a sp=$20)
srchmsg .byte $53,$45,$41,$52,$43,$48,$3a,$20  ;"SEARCH: " in lowercase/uppercase charset

; controls legend (search-page keys), drawn on the bottom two rows. drawleg
; converts each char to a screen code; .text case-inverts on display, so the
; source case is the opposite of what appears (e.g. "crsr" shows as "CRSR").
leg1 .text "crsr:MOVE  return:OPEN  f1/f7:PAGE"
     .byte 0
leg2 .text "TYPE TO FILTER  f2:DOCS  stop:EXIT"
     .byte 0

; doc-view status bar (drawn reverse-video by drawstatus). Exactly COLS chars so
; it fills the row; case-inverts on display ("f1/f7" -> "F1/F7", "PAGE" -> "page").
docleg .text "f1/f7:PAGE f3/f5:TOPIC f2:FIND stop:EXIT"
       .byte 0

;==================== variables ====================
;(live in the copied $c000 image; assembled with initial values)
topline  .word 0
totlines .word 0
lineidx  .word 0
wr       .byte 0
wrh      .byte 0
quot     .byte 0
wbank    .byte 0
row      .byte 0
mlo      .byte 0
mhi      .byte 0
dtmp     .word 0
sav01    .byte 0
savbln   .byte 0
savnmi   .word 0
savkey   .word 0      ;saved KEYLOG vector (MDBASIC's keychk)
savbdr   .byte 0      ;saved border color
savbg    .byte 0      ;saved background color
savfg    .byte 0      ;saved foreground color
savvmc   .byte 0      ;saved VMCSB (charset + video matrix)
savturbo .byte 0      ;saved Ultimate 64 turbo speed register ($d031)
savd3    .byte 0      ;saved cursor column (PNTR $d3)
savd6    .byte 0      ;saved cursor row (TBLX $d6)
pktmp    .byte 0      ;color pack scratch (high nybble being assembled)
mode     .byte 0      ;0=search page, 1=doc view
filtbuf  .repeat NAMELEN,0 ;active filter (screen codes)
filtlen  .byte 0
selvis   .byte 0      ;selected entry index (0-based, wraps in numvis)
scrolltop .byte 0     ;first logical grid row shown (scroll offset)
maxscr   .byte 0      ;max scrolltop for the current result count (F1/F7 paging)
selrow   .byte 0      ;selvis/NCOLS, computed by ensure_visible
gr_row   .byte 0      ;logical row of the entry being drawn (render_search)
gr_col   .byte 0      ;column (0..NCOLS-1) of the entry being drawn
numvis   .byte 0      ;count of filter-matching entries (set by render_search)
rscnt    .byte 0      ;loop counter for index scan routines
topdir   .byte 0      ;0=next, 1=prev (for dotopnav)
numtop   .byte 0      ;copy of IXCOUNT low byte for dotopnav
fscnt    .byte 0      ;visible entry counter for find_selected
fmpos    .byte 0      ;outer position for filtmatch substring search
bp       .byte 0      ;blank_tail position counter
bp_end   .byte 0      ;blank_tail window-end position
namebuf  .repeat NAMELEN,0 ;name buffer (screen codes)

; packed color-RAM snapshot: 1000 cells -> 500 bytes (see savecolor). Emitted as
; real image bytes so make_crt's PAGER_MAX check guards it from reaching SCRBUF
; ($cc00); it is written before it is read, so its initial contents don't matter.
COLBUF   .repeat 500,0

pgend
