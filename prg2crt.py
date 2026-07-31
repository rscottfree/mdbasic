import argparse
import binascii
import array

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

# output data array
crtData = bytearray() #crtData = b''

# helper function to write binary data to the CRT file
def writeHex(string):
	global crtData
	crtData += bytearray.fromhex(string)

# CRT signature
#         C  6  4     C  A  R  T  R  I  D  G  E
writeHex('43 36 34 20 43 41 52 54 52 49 44 47 45 20 20 20')

# header length (64 bytes)
writeHex('00 00 00 40')

# cartridge version
writeHex('01 00')

# cartridge hardware type: Magic Desk ID=19 ($13)
writeHex('00 13')

# EXROM status
writeHex('00')

# GAME status
writeHex('01')

# reserved
writeHex('00 00 00 00 00 00')

# cartridge name
#         M  D  B  A  S  I  C
writeHex('4d 44 42 41 53 49 43')
writeHex('00'*(32-7))

# ROM content
content = bytearray()

# add loader (from "loader.bin" file)
#loaderFile = open('loader.bin', 'rb')
#loader = loaderFile.read()
#content += bytearray(loader)
#print ''.join( [ "%02X " % ord( x ) for x in loader ] ).strip()

# add loader inline
content += bytearray.fromhex(
#  reset vector and run/stop vectors set to $8009
	'09 80 09 80' +
#  C  B  M  8  0
	'C3 C2 CD 38 30' +
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
 'BD 59 80' + #lda $8059,x
 '9D 00 04' + #sta $0400,x
 'E8 D0 F7' + #inx bne
 '4C 00 04' + #jmp $0400
 '00 00'    + #filler

#launcher at $8059
#copy cartridge ROM to C64 RAM
 '78'       + #sei
 'A2 00'    + #ldx #0
 'A5 57'    + #lda $57
 '8D 00 DE' + #sta $DE00
 'A1 5A'    + #lda ($5A),x
 '81 2D'    + #sta ($2D),x
 'E6 5A'    + #inc $5A
 'D0 13'    + #bne 
 'E6 5B'    + #inc $5B
 'A5 5B'    + #lda $5B
 'C9 A0'    + #cmp #$A0
 'D0 0B'    + #bne
 'A9 80'    + #lda #$80
 '85 5B'    + #sta $5B
 'E6 57'    + #inc $57
 'A5 57'    + #lda $57
 '8D 00 DE' + #sta $DE00
 'E6 2D'    + #inc $2D
 'D0 02'    + #bne
 'E6 2E'    + #inc $2E
 'C6 58'    + #dec $58
 'D0 DB'    + #bne
 'C6 59'    + #dec $59
 'A5 59'    + #lda $59
 'C9 FF'    + #cmp #$FF
 'D0 D3'    + #bne
 'A9 80'    + #lda #$80  #disable cartridge ROM
 '8D 00 DE' + #sta $DE00
 '58'       + #cli
 '6C FC FF' + #jmp ($fffc) #reset
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

# align to 0x2000 bytes
while (len(content) & 0x1fff) != 0:
	content.append(0)


# save content as 8K Chip blocks
banks = int(len(content) / 0x2000)
for bank in range(0, banks):
	#          C  H  I  P
	writeHex('43 48 49 50')
	
	# total packet length: 0x2010 (ROM image size + CHIP header)
	writeHex('00 00 20 10')
	
	# chip type: 0=ROM, 1=RAM only, 2=Flash ROM
	writeHex('00 00')
	
	# bank number
	crtData.append(0)
	crtData.append(bank)
	
	# starting load address $8000
	writeHex('80 00')
	
	# ROM image size 8K = $2000
	writeHex('20 00')
	
	# 0x2000 bytes ROM image
	start = 0x2000 * bank
	end = start + 0x2000
	crtData += content[start:end]

# save module
crt = open(outputFilename, 'wb')
crt.write(crtData)
crt.close()

