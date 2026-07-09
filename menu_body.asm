; ***MDBASIC CTRL+RESTORE menu-body UI***
; Copied to $c000 from the first tool bank's $9800 by the resident stub in
; menu.asm. This is the ONE place that snapshots screen RAM + cursor + blink
; state for the whole CTRL+RESTORE flow and, in full-UI mode, shows the prompt
; and returns the user's choice in X.
;
; It runs in one of two modes selected by SAVEONLY:
;
;   SAVEONLY = 0 (the real CTRL+RESTORE path): draws six menu lines
;   (one item per row) at the top of the screen with the blinking cursor
;   disabled (this is a GETIN read loop, not the screen editor -- there's no
;   real cursor to blink), reads one key, and returns the choice in X: 0 =
;   dismiss, 1 = docs pager, 2 = renumber, 3 = move, 4 = copy, 5 = convert.
;   On dismiss it restores the screen/cursor/blink itself; on F1/R/M/C/F7 it
;   leaves the saved pre-menu state intact for the dispatched tool's own exit
;   to restore.
;
;   SAVEONLY != 0 (dodocs/dorenum/domove/docopy in menu.asm): skips the UI and
;   just takes the snapshot, then returns immediately so the chosen tool still
;   has a valid restore snapshot.
;
; This runs before any tool is launched, so it is free to live in the tool
; region at $c000 and simply RTS to the resident stub.
;
; Same screen-snapshot idiom (SCRBUF $cc00, savhib SCREEN-1-5 fallback) as
; docs_pager.asm / edit_tool_common.asm; see the renum-move-tool design memory.
;
; Assembled for $c000 (run location).

R6510    = $01        ;set to $37 by the stub before entry (I/O + KERNAL in)
QTSW     = $d4        ;editor quote-mode flag
RVS      = $c7        ;editor reverse flag
INSRT    = $d8        ;editor insert count
KEYLOG   = $028f      ;keyboard decode-table setup vector (MDBASIC hooks this)
STDKEYLOG = $eb48     ;kernal's standard decode-table setup (raw F1-F8 codes)
GETIN    = $ffe4      ;kernal: read one key from the buffer (A=0 if none)
CLRSCR   = $e544      ;kernal clear screen
BLNSW    = $cc        ;cursor blink enable ($00=blinks, nonzero=disabled)
GDCHAR   = $ce        ;true char under a shown cursor block
BLNON    = $cf        ;cursor blink phase ($00=block shown, nonzero=char shown)
BLNCT    = $cd        ;cursor blink countdown (20 = one full period)
PNT      = $d1        ;pointer to the current screen line (lo/hi)
PNTR     = $d3        ;cursor column on the current line
TBLX     = $d6        ;cursor physical row
HIBASE   = $0288      ;screen page in use ($04 = standard $0400 text page)
SCREEN   = $0400
SCRBUF   = $cc00      ;1K snapshot of screen RAM -- same idiom/address as the
                      ;docs pager's / renum tool's SCRBUF (used sequentially,
                      ;never concurrently, so sharing it is safe)
SCROLY   = $d011
VMCSB    = $d018
CI2PRA   = $dd00
ROW0     = $0400      ;screen RAM row 0 (top line)
ROW1     = $0428      ;row 1
ROW2     = $0450      ;row 2
ROW3     = $0478      ;row 3
ROW4     = $04a0      ;row 4
ROW5     = $04c8      ;row 5
KEY_F1   = $85
KEY_F7   = $88
KEY_R    = "r"
KEY_M    = "m"
KEY_C    = "c"
KEY_STOP = $03
;--- shared CTRL+RESTORE handoff (also used by edit_tool_common.asm/docs_pager.asm) ---
;This save happens exactly once per invocation, here. The chosen tool's own
;exit reads these back to restore -- it never re-saves. Zero page: menu.asm's
;copyrun scratch ($02-$05,$fb-$fe) is transient and expires before this code
;runs; these addresses also avoid edit_tool_common.asm's persistent zero page (COUNT
;$0b, LINNUM $14, TXTTAB $2b, etc.) and docs_pager.asm's (TMP $02, SRCP $fb,
;SCRP $fd).
SAVEONLY = $0e        ;0 = full UI (below); nonzero = quick save-only path
SAVD3    = $06        ;saved PNTR (cursor column)
SAVD6    = $07        ;saved TBLX (cursor row)
SAVPNT   = $08        ;saved PNT lo($08)/hi($09)
SAVHIB   = $0a        ;saved HIBASE (screen page at CTRL+RESTORE time)
SAVBLN   = $0d        ;saved BLNSW (blink-enable state at CTRL+RESTORE time)

*=$c000

start
 lda SAVEONLY
 beq fullui           ;0 -> show the real F1/R/M/C/STOP menu
;--- quick save-only path (dodocs/dorenum/domove/docopy): snapshot and return ---
 jsr gethib
 sta SAVHIB
 jsr savescreen
 lda BLNSW
 sta SAVBLN
 rts

;--- full UI path ---
fullui
 lda KEYLOG           ;save + retarget the func-key decode vector
 sta svkey
 lda KEYLOG+1
 sta svkey+1
 lda #<STDKEYLOG
 sta KEYLOG
 lda #>STDKEYLOG
 sta KEYLOG+1
 lda #0               ;clear any active editor mode so the resumed editor is clean
 sta QTSW
 sta INSRT
 sta RVS
 jsr gethib           ;remember whether we're on the $0400 text screen (page 0)
 sta SAVHIB           ;or a SCREEN 1-5 page -- savescreen below is only meaningful
                      ;for page 0; a graphics page's content isn't recoverable
 jsr savescreen       ;snapshot screen RAM + cursor pos so we can put it back
 lda BLNSW            ;save + disable the blinking cursor for the menu's GETIN
 sta SAVBLN           ;loop -- there's no screen-editor cursor to move here, so
 lda #1               ;a blinking block over the menu would be misleading
 sta BLNSW
 jsr forcetext        ;canonical text mode / VIC bank 0 (in case graphics was on)
 jsr CLRSCR            ;blank screen to draw the menu prompt on
 ldx #PROMPT1LEN-1
draw1
 lda prompt1,x
 and #$3f             ;PETSCII -> screen code for our uppercase/space/digit/'=' set
 sta ROW0,x
 dex
 bpl draw1
 ldx #PROMPT2LEN-1
draw2
 lda prompt2,x
 and #$3f
 sta ROW1,x
 dex
 bpl draw2
 ldx #PROMPT3LEN-1
draw3
 lda prompt3,x
 and #$3f
 sta ROW2,x
 dex
 bpl draw3
 ldx #PROMPT4LEN-1
draw4
 lda prompt4,x
 and #$3f
 sta ROW3,x
 dex
 bpl draw4
 ldx #PROMPT5LEN-1
draw5
 lda prompt5,x
 and #$3f
 sta ROW4,x
 dex
 bpl draw5
 ldx #PROMPT6LEN-1
draw6
 lda prompt6,x
 and #$3f
 sta ROW5,x
 dex
 bpl draw6
 cli                  ;let the kernal IRQ scan the keyboard for GETIN
keyloop
 jsr GETIN
 ldx #1
 cmp #KEY_F1
 beq chosen
 ldx #2
 cmp #KEY_R
 beq chosen
 ldx #3
 cmp #KEY_M
 beq chosen
 ldx #4
 cmp #KEY_C
 beq chosen
 ldx #5
 cmp #KEY_F7
 beq chosen
 ldx #0
 cmp #KEY_STOP
 bne keyloop          ;ignore any other key
chosen
 stx svchoice
 sei
 cpx #0
 bne fin              ;F1/R/M/C chosen -> leave screen/cursor/blink saved as-is for
                      ;the dispatched tool's own exit to restore
 lda SAVHIB
 cmp #$04
 bne fromgfx          ;came from a SCREEN 1-5 page -- its content was never saved,
                      ;so leave the fresh $0400 screen for the chosen tool to reuse
 jsr restorescreen    ;put the true pre-menu screen back before dismissing
 lda SAVBLN
 sta BLNSW            ;resume the prior blink-enable state
 lda #$ff
 sta BLNON            ;char-shown phase: the resumed IRQ draws a fresh cursor
                      ;block, leaving no stale block artifact
 lda #1
 sta BLNCT            ;blink almost immediately
 jmp fin
fromgfx
 lda #$20             ;clean "no block, space underneath" cursor state, same as
 sta GDCHAR           ;the docs pager's / renum tool's SCREEN-1-5 exit idiom (the
 lda SAVBLN           ;fresh CLRSCR above already rebuilt the link table + homed
 sta BLNSW            ;PNT, so no second clear is needed here)
 lda #$ff
 sta BLNON
fin
 lda svkey            ;restore MDBASIC's func-key decode hook
 sta KEYLOG
 lda svkey+1
 sta KEYLOG+1
 ldx svchoice
 rts

;force canonical text screen (identical idiom to edit_tool_common.asm/docs_pager.asm)
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

gethib
 lda HIBASE
 bne gh_ok
 lda #$04
gh_ok
 rts

;==================== screen snapshot / restore ====================
;Same idiom as edit_tool_common.asm's savescreen/restorescreen. CLRSCR homes
;PNT/PNTR/TBLX, so (like the edit tools, unlike the pager) PNT must be
;explicitly saved and restored here rather than assumed undisturbed.
savescreen
 lda BLNON
 bne ss_pos           ;char shown (no block) -> cell already holds the real char
 ldy PNTR             ;block on screen -> restore the true char to the cursor cell
 lda GDCHAR
 sta (PNT),y          ;cell = (current line)+column
ss_pos
 lda PNTR
 sta SAVD3
 lda TBLX
 sta SAVD6
 lda PNT
 sta SAVPNT
 lda PNT+1
 sta SAVPNT+1
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

prompt1 .text "F1=DOCS"
PROMPT1LEN = *-prompt1
prompt2 .text "R=RENUMBER"
PROMPT2LEN = *-prompt2
prompt3 .text "M=MOVE"
PROMPT3LEN = *-prompt3
prompt4 .text "C=COPY"
PROMPT4LEN = *-prompt4
prompt5 .text "F7=CONVERT"
PROMPT5LEN = *-prompt5
prompt6 .text "STOP=QUIT"
PROMPT6LEN = *-prompt6
svkey .word 0
svchoice .byte 0
