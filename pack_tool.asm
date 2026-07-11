; ***MDBASIC PACKAGE tool***
; Launched from the CTRL+RESTORE menu (P). Writes the BASIC program currently
; in memory plus the resident 16K MDBASIC image into ONE self-contained PRG on
; the current disk device: LOAD"NAME",8,1 on a stock, cartridge-less C64
; auto-runs it exactly as if MDBASIC had been installed, the program loaded,
; and RUN typed. See pack_stub.asm (the embedded boot stub) for the file
; layout and autostart mechanics, and tools/pack_prg.py for the host-side twin
; that the VICE tests use as the byte-for-byte oracle.
;
; The tool streams the file through the KERNAL file API on device FA ($ba,
; the last-used disk device, minimum 8): an "S0:name" on the command channel
; first (so an existing file is overwritten), then OPEN "name,P,W" and CHROUT
; the sections in order: load address, IMAIN hook, the standard-vector block,
; the boot stub (progend patched on the fly), the screen banner block, the
; program bytes (TXTTAB..VARTAB-1), and the image ($8000-$bfff, read under the
; BASIC ROM with LORAM=0 -- the KERNAL+I/O stay in, which is all CHROUT's IEC
; path needs). While streaming $8002/$8003 it substitutes the original runstp
; vector stashed at REALGONE if the boot loader repointed it at the $033c menu
; handler: the packaged machine has no cart banks, so the handler would be
; garbage there.
;
; The embedded stub template (build/pack_stub.inc, generated from
; pack_stub.bin by tools/bin2inc.py) still carries the $caf1/$caf2
; newvec/initclk jsr sentinels at this point; tools/make_crt.py patches them
; inside this tool's assembled binary, so what streams out is fully resolved.
;
; RUN/STOP at the filename prompt cancels. Any disk error surfaces on the
; drive-status line printed after the write. Copied to $c000 by the resident
; stub; RTSs back to it for the single NMI-tail RTI.
; Assembled for $c000 (run location); must stay < $cc00 (SCRBUF).

R6510    = $01
TXTTAB   = $2b        ;start of BASIC program text
VARTAB   = $2d        ;end of program + 1 (start of variables)
STRP     = $26
FA       = $ba        ;last-used device number
BLNSW    = $cc        ;cursor blink enable ($00=blinks, nonzero=disabled)
GDCHAR   = $ce
BLNON    = $cf
BLNCT    = $cd
PNT      = $d1
PNTR     = $d3
TBLX     = $d6
HIBASE   = $0288
NMIVEC   = $0318
REALGONE = $03f8      ;original runstp (lo,hi), stashed by the cart boot loader
HANDLER  = $033c      ;where the loader points $8002 when the menu is installed
SCREEN   = $0400
SCRBUF   = $cc00
SCROLY   = $d011
VMCSB    = $d018
CI2PRA   = $dd00
CLRSCR   = $e544
READST   = $ffb7
SETLFS   = $ffba
SETNAM   = $ffbd
OPEN     = $ffc0
CLOSE    = $ffc3
CHKIN    = $ffc6
CHKOUT   = $ffc9
CLRCHN   = $ffcc
CHRIN    = $ffcf
CHROUT   = $ffd2
GETIN    = $ffe4
CLALL    = $ffe7
SRCP     = $fb        ;stream pointer (free zp: copyrun's scratch has expired)

;--- shared CTRL+RESTORE-menu screen/cursor/blink handoff (see menu_body.asm) ---
SAV01    = $05        ;resident stub's saved original $01
SAVD3    = $06        ;saved PNTR (cursor column)
SAVD6    = $07        ;saved TBLX (cursor row)
SAVPNT   = $08        ;saved PNT lo($08)/hi($09)
SAVHIB   = $0a        ;saved HIBASE (screen page at CTRL+RESTORE time)
SAVBLN   = $0d        ;saved BLNSW (blink-enable state at CTRL+RESTORE time)

;--- packaged-file layout constants (keep in sync with tools/pack_prg.py) ---
STUBSIZE = 204        ;stub region $0334-$03ff in the packaged file
PGOFF    = 3          ;progend word offset inside the stub
NAMEMAX  = 16
LFCMD    = 15         ;command-channel logical file
LFDATA   = 2          ;write-channel logical file

*=$c000

;==================== entry ====================
start
 lda #$37
 sta R6510            ;BASIC+KERNAL+I/O in
 lda #1
 sta BLNSW            ;no blinking cursor: this is a GETIN loop, not the editor
 lda NMIVEC           ;park the NMI vector on an RTI so a second RESTORE press
 sta savnmi           ;can't re-enter the menu stub while we're running
 lda NMIVEC+1
 sta savnmi+1
 lda #<nmistub
 sta NMIVEC
 lda #>nmistub
 sta NMIVEC+1
 cli                  ;kernal IRQ keyscan feeds GETIN
 lda SAVHIB           ;keep our own copies: the handoff zp survives, but the
 sta svhib            ;idiom (convert_tool.asm) copies once at entry
 lda SAVBLN
 sta svbln
 jsr forcetext
 jsr CLRSCR
 lda #<hdrtxt
 ldy #>hdrtxt
 jsr prstrAY
;program present? (an empty program is just the $00,$00 end marker)
 lda VARTAB
 sec
 sbc TXTTAB
 sta plen
 lda VARTAB+1
 sbc TXTTAB+1
 sta plen+1
 bne havepgm
 lda plen
 cmp #3
 bcs havepgm
 lda #<snoprg
 ldy #>snoprg
 jsr prstrAY
 jmp waitexit

;==================== filename prompt ====================
havepgm
 lda FA               ;current device, floor 8 (FA can be tape/screen)
 cmp #8
 bcs devok
 lda #8
devok
 sta dev
 lda #<sdev
 ldy #>sdev
 jsr prstrAY
 lda dev              ;print device number (8-30: two digits max)
 ldx #"0"-1
tens
 inx
 sec
 sbc #10
 bcs tens
 adc #10+"0"          ;a = ones digit
 pha
 cpx #"0"
 beq ones
 pha
 txa
 jsr CHROUT
 pla
ones
 pla
 jsr CHROUT
 lda #$0d
 jsr CHROUT
prompt
 lda #<sname
 ldy #>sname
 jsr prstrAY
 jsr readline
 bcs cancel
 lda bufi
 beq prompt           ;empty name: ask again
 jmp dowrite
cancel
 jmp texit

;==================== write the packaged file ====================
dowrite
 lda #<swrite
 ldy #>swrite
 jsr prstrAY
 jsr CLALL            ;clean logical-file table before opening ours
;scratch any existing file: command channel OPEN with "S0:name"
 lda #"s"
 sta cmdbuf
 lda #"0"
 sta cmdbuf+1
 lda #":"
 sta cmdbuf+2
 ldx #0
cpn1
 lda inbuf,x
 sta cmdbuf+3,x
 inx
 cpx bufi
 bne cpn1
 txa
 clc
 adc #3
 ldx #<cmdbuf
 ldy #>cmdbuf
 jsr SETNAM
 lda #LFCMD
 ldx dev
 ldy #15
 jsr SETLFS
 jsr OPEN
 bcc scrok            ;device not present etc.
digain
 jmp diskerr
scrok
;write channel: "name,P,W"
 ldx #0
cpn2
 lda inbuf,x
 sta cmdbuf,x
 inx
 cpx bufi
 bne cpn2
 lda #","
 sta cmdbuf,x
 lda #"p"
 sta cmdbuf+1,x
 lda #","
 sta cmdbuf+2,x
 lda #"w"
 sta cmdbuf+3,x
 txa
 clc
 adc #4
 ldx #<cmdbuf
 ldy #>cmdbuf
 jsr SETNAM
 lda #LFDATA
 ldx dev
 ldy #2
 jsr SETLFS
 jsr OPEN
 bcs digain
 ldx #LFDATA
 jsr CHKOUT
 bcs digain
;--- section 1: load address $0302 + IMAIN hook -> $0334 ---
 ldy #0
hdrlp
 lda hdr4,y
 jsr CHROUT
 iny
 cpy #4
 bne hdrlp
;--- section 2: the standard vector block $0304-$0333 ---
 ldy #0
veclp
 lda vectab,y
 jsr CHROUT
 iny
 cpy #48
 bne veclp
;--- section 3: boot stub $0334-$03ff, progend patched on the fly ---
;progend = $0801 + program length (where the image section lands in the file)
 lda plen
 clc
 adc #$01
 sta pgend
 lda plen+1
 adc #$08
 sta pgend+1
 ldy #0
stublp
 lda #0               ;past the template: zero fill up to $0400
 cpy #STUBTPL_LEN
 bcs stput
 lda stubtpl,y
stput
 cpy #PGOFF
 bne stnot3
 lda pgend
stnot3
 cpy #PGOFF+1
 bne stnot4
 lda pgend+1
stnot4
 jsr CHROUT
 iny
 cpy #STUBSIZE
 bne stublp
;--- section 4: screen block $0400-$07ff (spaces + banner row) ---
;banner sits at offset 12*40+8 = 488 = 244+244; then 24 banner chars; then
;1024-488-24 = 512 = 256+256 spaces (see tools/pack_prg.py)
 ldx #244
 jsr wrspaces
 ldx #244
 jsr wrspaces
 ldy #0
banlp
 lda banner,y
 and #$3f             ;PETSCII uppercase -> screen code (space stays $20)
 jsr CHROUT
 iny
 cpy #24
 bne banlp
 ldx #0               ;256
 jsr wrspaces
 ldx #0               ;256
 jsr wrspaces
;--- section 5: the $00 byte before BASIC text ($0800) ---
 lda #0
 jsr CHROUT
;--- section 6: program bytes TXTTAB..VARTAB-1 (plen of them) ---
 lda TXTTAB
 sta SRCP
 lda TXTTAB+1
 sta SRCP+1
 lda plen
 sta cnt
 lda plen+1
 sta cnt+1
 ldy #0
pgmlp
 lda cnt
 ora cnt+1
 beq pgmdone
 lda (SRCP),y
 jsr CHROUT
 inc SRCP
 bne pgm1
 inc SRCP+1
pgm1
 lda cnt
 bne pgm2
 dec cnt+1
pgm2
 dec cnt
 jmp pgmlp
pgmdone
 jsr wrdot            ;program section done: first progress dot
;--- section 7: the 16K image $8000-$bfff ---
;$8002/$8003 substitution: if the cart boot loader repointed the image's NMI
;vector at the $033c menu handler, emit the original runstp from REALGONE --
;the packaged machine has no cart, so the handler never exists there.
 lda $8002
 sta vec2
 lda $8003
 sta vec3
 cmp #>HANDLER
 bne vecok
 lda $8002
 cmp #<HANDLER
 bne vecok
 lda REALGONE
 sta vec2
 lda REALGONE+1
 sta vec3
vecok
 lda #$00
 sta SRCP
 lda #$80
 sta SRCP+1
 lda R6510
 and #%11111110
 sta R6510            ;LORAM=0: image RAM readable at $a000-$bfff; KERNAL+I/O
                      ;stay in, which is all the IEC write path needs
;first page carries the $8002/$8003 substitution
 ldy #0
img1lp
 lda (SRCP),y
 cpy #2
 bne img1a
 lda vec2
img1a
 cpy #3
 bne img1b
 lda vec3
img1b
 jsr CHROUT
 iny
 bne img1lp
 inc SRCP+1
;remaining 63 pages, a progress dot every 4
 ldx #63
imglp
 ldy #0
imgblp
 lda (SRCP),y
 jsr CHROUT
 iny
 bne imgblp
 inc SRCP+1
 txa
 and #%00000011
 bne img2
 stx xsave
 jsr wrdot
 ldx xsave
img2
 dex
 bne imglp
 inc R6510            ;BASIC ROM back in
;--- close + status ---
 jsr CLRCHN
 lda #LFDATA
 jsr CLOSE
 lda #$0d
 jsr CHROUT
;read the drive status line into stbuf, then print it
 ldx #LFCMD
 jsr CHKIN
 bcs stdone
 ldy #0
stlp
 jsr CHRIN
 cmp #$0d
 beq stgot
 sta stbuf,y
 iny
 cpy #38
 bne stlp
stgot
 lda #0
 sta stbuf,y
 jsr CLRCHN
 lda #<stbuf
 ldy #>stbuf
 jsr prstrAY
 lda #$0d
 jsr CHROUT
stdone
 lda #LFCMD
 jsr CLOSE
 lda #<sdone
 ldy #>sdone
 jsr prstrAY
 jmp waitexit

;disk error (device not present / open failed)
diskerr
 lda R6510
 ora #%00000001
 sta R6510            ;BASIC ROM back in if the image pass turned it off
 jsr CLRCHN
 lda #LFDATA
 jsr CLOSE
 lda #LFCMD
 jsr CLOSE
 lda #<sderr
 ldy #>sderr
 jsr prstrAY
waitexit
 lda #<skey
 ldy #>skey
 jsr prstrAY
wkey
 jsr GETIN
 beq wkey
;==================== exit ====================
texit
 lda savnmi
 sta NMIVEC
 lda savnmi+1
 sta NMIVEC+1
 lda svhib
 cmp #$04
 bne tblank           ;a SCREEN 1-5 page was never snapshotted: fresh screen
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

;==================== helpers ====================
;write X spaces (screen codes) to the open channel; X=0 means 256
wrspaces
 lda #$20
 jsr CHROUT
 dex
 bne wrspaces
 rts

;progress dot on the screen: park the file channel, print, resume
wrdot
 tya
 pha
 jsr CLRCHN
 lda #"."
 jsr CHROUT
 ldx #LFDATA
 jsr CHKOUT
 pla
 tay
 rts

;force canonical text screen (same idiom as menu_body.asm/convert_tool.asm)
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
;same GETIN readline idiom as convert_tool.asm, capped at 16 chars and
;filtering the drive-special characters out of filenames
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
 cmp #$80             ;$20-$7f are printable -- maybe
 bcs rl_lp            ;$80+: shifted control codes / graphics -- ignore
 ldx #BADCHN-1
rl_bad
 cmp badch,x
 beq rl_lp            ;drive-special char: not valid in a filename
 dex
 bpl rl_bad
 ldx bufi
 cpx #NAMEMAX
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
 clc
 rts
rl_stop
 jsr hidecursor
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

;text authored lowercase so tmpx emits PETSCII $41-$5a (displays uppercase)
hdrtxt
 .text "mdbasic package"
 .byte $0d
 .text "writes mdbasic + the program in memory"
 .byte $0d
 .text "as one self-running prg (load ...,8,1)."
 .byte $0d, $0d, $00
snoprg .text "no program in memory."
 .byte $0d, $00
sdev .null "device: "
sname .null "filename: "
swrite
 .byte $0d
 .text "writing"
 .null " "
sderr
 .byte $0d
 .text "?device error"
 .byte $0d, $00
sdone .text "done."
 .byte $0d, $00
skey .null "press any key."

badch .text "@*?=:;,"
 .byte $22            ;quote
BADCHN = *-badch

;--- packaged-file fixed blocks (keep in sync with tools/pack_prg.py) ---
hdr4 .byte $02,$03,$34,$03   ;PRG load address $0302, then IMAIN -> $0334
;$0304-$0333 standard vector values: BASIC indirects, USR jump, KERNAL table.
;Loading these over the live vectors is safe because every byte written equals
;the byte already there (the IRQ vector included).
vectab
 .byte $7c,$a5        ;$0304 ICRNCH
 .byte $1a,$a7        ;$0306 IQPLOP
 .byte $e4,$a7        ;$0308 IGONE
 .byte $86,$ae        ;$030a IEVAL
 .byte $00,$00,$00,$00 ;$030c SAREG/SXREG/SYREG/SPREG
 .byte $4c,$48,$b2    ;$0310 USR jmp $b248
 .byte $00            ;$0313
 .byte $31,$ea        ;$0314 CINV
 .byte $66,$fe        ;$0316 CBINV
 .byte $47,$fe        ;$0318 NMINV
 .byte $4a,$f3        ;$031a IOPEN
 .byte $91,$f2        ;$031c ICLOSE
 .byte $0e,$f2        ;$031e ICHKIN
 .byte $50,$f2        ;$0320 ICKOUT
 .byte $33,$f3        ;$0322 ICLRCH
 .byte $57,$f1        ;$0324 IBASIN
 .byte $ca,$f1        ;$0326 IBSOUT
 .byte $ed,$f6        ;$0328 ISTOP
 .byte $3e,$f1        ;$032a IGETIN
 .byte $2f,$f3        ;$032c ICLALL
 .byte $66,$fe        ;$032e USRCMD
 .byte $a5,$f4        ;$0330 ILOAD
 .byte $ed,$f5        ;$0332 ISAVE
banner .text "mdbasic packaged program"   ;24 chars, row 12 col 8

;the boot stub template (pack_stub.bin; newvec/initclk sentinels patched into
;this tool's binary by tools/make_crt.py)
.include "build/pack_stub.inc"

;==================== state ====================
savnmi .word 0
svhib  .byte 0
svbln  .byte 0
dev    .byte 0
bufi   .byte 0
plen   .word 0
pgend  .word 0
cnt    .word 0
vec2   .byte 0
vec3   .byte 0
xsave  .byte 0
inbuf  .repeat NAMEMAX+1,0
cmdbuf .repeat NAMEMAX+8,0
stbuf  .repeat 40,0
