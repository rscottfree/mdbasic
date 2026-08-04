import argparse
import binascii
import array

# helper function to write binary data to the CRT file
def writeHex(string):
	global crtData
	crtData += bytearray.fromhex(string)

# command line parsing
parser = argparse.ArgumentParser(description='Converts C64 PRG to a CRT file.')
parser.add_argument('input.prg', action = 'store')
parser.add_argument('output.crt', action = 'store')
args = parser.parse_args()
inputFilename = args.__dict__['input.prg']
outputFilename = args.__dict__['output.crt']

# open PRG file and read into array
inputFile = open(inputFilename, 'rb')
prg = bytearray(inputFile.read())

# CRT signature (16 bytes)
# "C64 CARTRIDGE   " C64 cartridge
# "C128 CARTRIDGE  " C128 cartridge (added in v2.0)
# "CBM2 CARTRIDGE  " CBMII cartridge (added in v2.0)
# "VIC20 CARTRIDGE " VIC20 cartridge (added in v2.0)
# "PLUS4 CARTRIDGE " C16/PLUS4 cartridge (added in v2.0)
crtData = bytearray(b'C64 CARTRIDGE   ')

# header length (32-bit value = 64)
writeHex('00 00 00 40')

# cartridge version (2-byte value for v1.0 specs)
writeHex('01 00')

# cartridge hardware type: (16-bit value = 19 ($13) for Magic Desk
writeHex('00 13')

# EXROM and GAME line statuses
#exrom/game status
#  0    0   16k Game
#  0    1    8k Game
#  1    0    ultimax
#  1    1    ram/off
writeHex('00 00')

# reserved
writeHex('00 00 00 00 00 00')

# cartridge name (32 bytes)
crtData += bytearray(b'MDBASIC')
writeHex('00'*(32-7))

# Begin ROM content
# add loader inline
content = bytearray.fromhex(
# reset vector and run/stop vectors set to $8009
	'09 80 09 80' +
	'C3 C2 CD 38 30' + # CBM80
# assembly lanaguage routine at $8009 to load RAM from cartridge ROM then run
# init BASIC
 '78'       + #sei
 'D8'       + #cld
# clear the stack
 'A2 FB'    + #ldx #$FB
 '9A'       + #txs
#init hardware devices and system RAM pointers
 '20 A3 FD' + #jsr $FDA3  #Initialize CIA I/O Devices
 '20 50 FD' + #jsr $FD50  #initialize RAM, tape buffer, screen
 'A9 A0'    + #lda #$A0
 '8D 84 02' + #sta $0284  #Hi-Byte of Pointer: O.S. End of Memory
 '20 15 FD' + #jsr $FD15  #restore default I/O vectors
 '20 5B FF' + #jsr $FF5B  #Initialize Screen Editor and VIC-II Chip
 '58'       + #cli
#blank the screen
 'AD 11 D0' + #lda SCROLY
 '29 EF'    + #and #%11101111  ;bit4 = 0 screen off
 '8D 11 D0' + #sta SCROLY

# prepare to copy cartrige ROM to C64 RAM
 'A9 00'    + #lda #$00
 '85 57'    + #sta $57
 'AD 9A 80' + #lda $809A
 '85 58'    + #sta $58
 'AD 9B 80' + #lda $809B
 '85 59'    + #sta $59
 'AD 9C 80' + #lda $809C
 '85 2D'    + #sta $2D
 'AD 9D 80' + #lda $809D
 '85 2E'    + #sta $2E
 'A9 9E'    + #lda #$9E
 '85 5A'    + #sta $5A
 'A9 80'    + #lda #$80
 '85 5B'    + #sta $5B
 'A2 00'    + #ldx #0
 'BD 59 80' + #copy lda $8059,x
 '9D 00 04' + #sta $0400,x
 'E8'       + #inx
 'D0 F7'    + #bne copy
 '4C 00 04' + #jmp $0400
 '00 00'    + #filler

#launcher at $8059
#copy cartridge ROM to C64 RAM
 '78'       + #sei
 'A2 00'    + #ldx #0
 'A5 57'    + #lda $57
 '8D 00 DE' + #sta $DE00  ;bits 0-6 used to select mem bank
 'A1 5A'    + #loop1 lda ($5A),x
 '81 2D'    + #sta ($2D),x
 'E6 5A'    + #inc $5A
 'D0 13'    + #bne go1
 'E6 5B'    + #inc $5B
 'A5 5B'    + #lda $5B
 'C9 A0'    + #cmp #$A0
 'D0 0B'    + #bne go1
 'A9 80'    + #lda #$80
 '85 5B'    + #sta $5B
 'E6 57'    + #inc $57
 'A5 57'    + #lda $57
 '8D 00 DE' + #sta $DE00
 'E6 2D'    + #go1 inc $2D
 'D0 02'    + #bne go2
 'E6 2E'    + #inc $2E
 'C6 58'    + #go2 dec $58
 'D0 DB'    + #bne loop1
 'C6 59'    + #dec $59
 'A5 59'    + #lda $59
 'C9 FF'    + #cmp #$FF
 'D0 D3'    + #bne loop1
 'A9 80'    + #lda #$80  ;bit7 set to 1 to disable cartridge ROM
 '8D 00 DE' + #sta $DE00
 '58'       + #cli
 '6C FC FF' + #jmp ($fffc) ;kernal soft reset
 '00 00 00 00' #filler
)

#data starting at $809A
# add program size, minus the first two bytes for start address
size = len(prg) - 2
#align to next page boundary (next 256 byte block)
content.append(size & 0xff)
content.append(int(size / 0x100))

# add program, with start address
content += prg

romImageSize = 0x2000  #typically $2000 (8K) or $4000 (16K)
packetSize = romImageSize + 0x10

# align to romImageSize bytes
while (len(content) & (romImageSize-1)) != 0:
	content.append(0)

# save content in blocks of romImageSize
banks = int(len(content) / romImageSize)
for bank in range(0, banks):
	crtData += bytearray(b'CHIP')
	
	# total packet size (32 bits in big-endian format)
	# this is the ROM image size + CHIP header size ($10)
	crtData.append(int(packetSize / 0x100000000))
	crtData.append(int(packetSize / 0x10000))
	crtData.append(int(packetSize / 0x100))
	crtData.append(packetSize & 0xff)
	
	# chip type (16-bit value)
	writeHex('00 00') # 0=ROM, 1=RAM only, 2=Flash ROM, 3=EEPROM
	
	# bank number (16-bit value)
	crtData.append(0)     # hibyte always zero
	crtData.append(bank)  # lobyte
	
	# starting load address $8000 (big-endian format)
	writeHex('80 00')
	
	# ROM image size (big-endian format)
	crtData.append(int(romImageSize / 0x100)) #hibyte
	crtData.append(romImageSize & 0xff) #lobyte

	# append bytes to ROM image
	start = romImageSize * bank
	end = start + romImageSize
	crtData += content[start:end]

# save module
crt = open(outputFilename, 'wb')
crt.write(crtData)
crt.close()

