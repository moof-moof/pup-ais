#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Filename: PupAIS_eee_mb.py


__version__ = '$Revision: 46.1 $'
__date__ = '$Date: 2011-10-25 $'
__author__ = 'Martin Bergman'
__doc__ = '''

PupAIS is a Python AIS NMEA string parser.
-------------------------------------------------------------------
This version outputs data to a csv file, which is parsed by two in-
dependent GUI's started as subprocesses in circa line 1150: 
1) PopuLister, a PythonCard script (AISflukt.py) listing data for each target,
2) Ployplot, a Pygame based "radar screen" emulator plotting  targets in 2D.
-------------------------------------------------------------------

@author: U{'''+__author__+'''<http://goto.glocalnet.net/mabe/>}
@version: ''' + __version__ +'''
@copyright: Certain functions adapted from code by
1) Bartek Górny <bartek@gorny.edu.pl> 2009
2) Robert Montante <bobmon@bloomu.edu> 2008
@status: under development
@license: GPL
'''



from decimal import *
from math import *
from pyglet import gl, image, text as tt, window as ww
import time
import operator 
import subprocess
import os
import serial


# ##################################################################
# ------------------------- Functions ------------------------------
# ##################################################################

def negate_2s_compl( binary_string ):
	
	''' Standard binary negation: complement all the bits, add 1.

		Algorithm:
		1) First invert all bits
		2) "Add 1" to Least Significant bit by:
		A) Start at rightmost bit, re-invert each '1';
		B) Re-invert rightmost '0' and stop there.

		This code builds "negated_string" as a _list_ of bits,
		then converts the list to a string.
		(Python handles lists better than strings.)
	'''
	negated_string = []

	for b in binary_string:     # Invert all bits, left to right
		negated_string.append( bitComplement[b] )

	for i in range(len(negated_string)-1, -1, -1):  # start at right, work left
		if negated_string[i] == '1':
			negated_string[i] = '0'
		else:
			negated_string[i] = '1'
		break       # Re-invert the rightmost '0', then stop.

	return ''.join(negated_string)  # turn list of chars into text string


'''
-------------------------------------------------------------------
The following three functions return signed decimal representations 
of a two's complimentary bitstring of arbitrary length.
-------------------------------------------------------------------
'''

def lon_2sC_Decoder( bitString ):
	''' Takes an arbitrary length string of signed two's complement
	binary numeric value.
	
	Returns a decimal Longitude (East/West) formatted position string.
	'''
	global spurio
	
	if bitString[0] == '1':
		isNegative = True
		magnitude_BINA = negate_2s_compl( bitString[1:])
	else:
		isNegative = False
		magnitude_BINA = bitString

	magnitude_DECI = str(round(int(magnitude_BINA , base=2)/Decimal(600000), 6))

	if float(magnitude_DECI) >= float('180.0'):    # Avoid comparing strings for size
		magnitude_DECI = '0.0'
		spurio = '02'    # Flag: Something is utterly wrong here! (Goofy LON vslue)
	else:
		spurio = 'ok'
	if isNegative:
		magnitude_DECI = ''.join(magnitude_DECI + ' W')
	else:
		magnitude_DECI = ''.join(magnitude_DECI + ' E')
			
	return magnitude_DECI
	

def lat_2sC_Decoder( bitString ):
	''' Takes an arbitrary length string of signed two's complement
	binary numeric value.
	
	Returns a decimal Latitude (North/South) formatted position string.
	'''
	global spurio

	if bitString[0] == '1':
		isNegative = True
		magnitude_BINA = negate_2s_compl( bitString[1:])
	else:
		isNegative = False
		magnitude_BINA = bitString

	magnitude_DECI = str(round(int(magnitude_BINA , base=2)/Decimal(600000), 6))
	
	if float(magnitude_DECI) >= float('90.0'):
		magnitude_DECI = '0.0'
		spurio = '01'	# Flag: Something is utterly wrong here! (Goofy LAT value)
	else:
		spurio = 'ok'
	if isNegative:
		magnitude_DECI = ''.join(magnitude_DECI + ' S')
	else:
		magnitude_DECI = ''.join(magnitude_DECI + ' N')
			
	return magnitude_DECI
	

def rot_2sC_Decoder( bitString ):
	''' Takes an arbitrary length string of signed two's complement
	binary numeric value.
	
	Returns a decimal rotation value, as a port/starboard formatted string.
	'''

	if  '1' not in bitString:
		magnitude_DECI = '--'
		
	elif bitString == '10000000':
		magnitude_DECI = '--'
		
	else:
		
		if bitString[0] == '1':
			isNegative = True
			magnitude_BINA = negate_2s_compl( bitString[1:])
		else:
			isNegative = False
			magnitude_BINA = bitString

		magnitude_DECI = str(trunc(((int(magnitude_BINA, base=2))/ Decimal(4733)*1000)**2))
		
		if isNegative:
			magnitude_DECI = ''.join('<-- ' + magnitude_DECI + ' <--')
		else:
			magnitude_DECI = ''.join('--> ' + magnitude_DECI + ' -->')
			
	return magnitude_DECI
	


def sog_cog_BinValueDecoder( bitString ):
	''' Takes an arbitrary length string of binary numeric value.
	
	Returns a decimal value, as a string.
	'''      
	magnitude_BINA = bitString

	magnitude_DECI = str((int(magnitude_BINA , base=2))/Decimal (10))

	return magnitude_DECI

def checkSumCheck(sentence):
	''' Verifies the data integrity checksum for an NMEA 0183 sentence.
	
	Returns the nmea data, the sentence checksum, and the calculated checksum. 
	'''

	skip, sentence = sentence.split ('!', 1)
	if sentence.find('\n'):
		sentence = sentence.strip('\n')
	if sentence.find('\r'):
		sentence = sentence.strip('\r')
	if sentence.find('"'):
		sentence = sentence.rstrip('"')

	nmeadata, cksum = sentence.split ('*', 1)
	calc_cksum = reduce(operator.xor, (ord(s) for s in nmeadata), 0)

	return nmeadata, int(cksum, 16), calc_cksum

	
def int2bin(n, count=6):
	''' Returns the binary of integer value n, using count number of digits.
	'''
	
	return ''.join([str((n >> y) & 1) for y in range(count-1, -1, -1)])


def str2Bitstr(s):
	return ''.join(s)

def sixBit2ASCIIchar(sxb):
	''' Takes a string of 120 bits.
	
	Returns a string of chars mapped from the NMEA ASCII 
	"Sixbit" chars set.
	'''
	
	sixBitASCIIdict = {'000000' : '@','000001' : 'A','000010' : 'B','000011' : 'C','000100' : 'D','000101' : 'E','000110' : 'F','000111' : 'G','001000' : 'H','001001' : 'I','001010' : 'J','001011' : 'K','001100' : 'L','001101' : 'M','001110' : 'N','001111' : 'O','010000' : 'P','010001' : 'Q','010010' : 'R','010011' : 'S','010100' : 'T','010101' : 'U','010110' : 'V','010111' : 'W','011000' : 'X','011001' : 'Y','011010' : 'Z','011011' : '[','011100' : '\\','011101' : ']','011110' : '\^','011111' : '_','100000' : ' ','100001' : '!','100010' : '"','100011' : '\#','100100' : '$','100101' : '%','100110' : '&','100111' : '\'','101000' : '(','101001' : ')','101010' : '\*','101011' : '\+','101100' : ',','101101' : '-','101110' : '.','101111' : '/','110000' : '0','110001' : '1','110010' : '2','110011' : '3','110100' : '4','110101' : '5','110110' : '6','110111' : '7','111000' : '8','111001' : '9','111010' : ':','111011' : ';','111100' : '<','111101' : '=','111110' : '>','111111' : '?'}

		
	SXB = []
	asciiChars = []

	for i in range(len(sxb)/6):
		temp = sxb[:6]
		temp.join(temp)
		SXB.append(temp)
		sxb = sxb[6:]

	for i in SXB:
		if i in sixBitASCIIdict:
			if i != '000000':
				temp2 = sixBitASCIIdict[i]
				asciiChars.append(temp2)
		else:
			print 'Say what?'
		
	return ''.join(asciiChars)
	

def sixBit2ICAO(sxb):
	''' Takes a string of 42 bits (7 sixbit chars).
	
	Returns a verbose string spelled out in ICAO "signalese"!
	'''
	
	verboseDict = {'000000' : '@','000001' : '-Alfa','000010' : '-Bravo','000011' : '-Charlie','000100' : '-Delta','000101' : '-Echo','000110' : '-Foxtrot','000111' : '-Golf','001000' : '-Hotel','001001' : '-India','001010' : '-Juliet','001011' : '-Kilo','001100' : '-Lima','001101' : '-Mike','001110' : '-November','001111' : '-Oscar','010000' : '-Papa','010001' : '-Quebec','010010' : '-Romeo','010011' : '-Sierra','010100' : '-Tango','010101' : '-Uniform','010110' : '-Victor','010111' : '-Whiskey','011000' : '-XRay','011001' : '-Yankee','011010' : '-Zulu','011011' : '[','011100' : '\\','011101' : ']','011110' : '\^','011111' : 'g\_','100000' : ' ','100001' : '!','100010' : '"','100011' : '\#','100100' : '$','100101' : '%','100110' : '&','100111' : '\'','101000' : '(','101001' : ')','101010' : '\*','101011' : '\+','101100' : ',','101101' : '-','101110' : '.','101111' : '/','110000' : '-0','110001' : '-1','110010' : '-2','110011' : '-3','110100' : '-4','110101' : '-5','110110' : '-6','110111' : '-7','111000' : '-8','111001' : '-9','111010' : ':','111011' : ';','111100' : '<','111101' : '=','111110' : '>','111111' : '?'}
		
	SXB = []
	asciiSpell = []

	for i in range(len(sxb)/6):
		temp = sxb[:6]
		temp.join(temp)
		SXB.append(temp)
		sxb = sxb[6:]

	for i in SXB:
		if i in verboseDict:
			if i != '000000':
				temp2 = verboseDict[i]
				asciiSpell.append(temp2)
		else:
			print 'Say again?'

	return ''.join(asciiSpell)##, SXB




def decapsulate(input):	

	'''
	Accepts an NMEA 0183-formatted AIS message sentence, 
	(i.e. a VDM encapsulated packet string).
	
	Returns the total count of sentence fragments of the arriving 
	message; the present fragments's number; a sequential 
	message ID for multi-sentence messages; and a list of the 
	significant binary digits in the sentence payload field.
	'''


# (1) Cut off the end flag and checksum. We don't need them here.
	z1 = input.find(',0*')
	shortString = input[:z1] 
	
# (2) Discard with the leading fluff (if any) including "!AIV..." tag.
	a1 = input.find('!AIV')
	a2 = 7 + a1
	shortString = shortString[a2:]

# (3) Save the usable fields.
	shortList = []
	shortList = shortString.split(',')
	_partsCount = shortList[0] ## Count of sentence parts
	_partNumber = shortList[1] ## 1 normally; 1, 2 etc for multi
	_sequentID = shortList[2]  ## Sequential Message ID for multi
	shortString = shortList[4] ## The message's essential data part

# (4) Convert the "valid characters" of the disassembled encapsulated
#     string into the sixbit binary strings they represent.
	list_8bit_ascii_ords = []
	for t in shortString[:]:
		list_8bit_ascii_ords.append(ord(t))

	list_minus48 = []
	for i in list_8bit_ascii_ords:
		list_minus48.append(i - 48)

	list_6bit_DEC = []
	for i in list_minus48:
		if i > 40:
			i = i - 8
			list_6bit_DEC.append(i)
		else:
			list_6bit_DEC.append(i)  

	list_6bit_BIN = []
	for i in list_6bit_DEC:
		list_6bit_BIN.append(int2bin(i))

# (5) Reassemble the sixbit strings into a single binary string.
	list_AllBits = []
	for i in list_6bit_BIN:
		
		lst = list(i)
		list_AllBits = list_AllBits + lst


	return _partsCount,_partNumber,_sequentID,list_AllBits



def statusCode2text(ns):
	''' Translates the navstatus code to it's text representation
	'''
	
	legend = ''
	if ns == 0:
		legend = 'Steaming'
	elif ns == 1:
		legend = 'At anchor'
	elif ns == 2:
		legend = 'Not under command'
	elif ns == 3:
		legend = 'Restricted maneuverability'
	elif ns == 4:
		legend = 'Constrained by draught'
	elif ns == 5:
		legend = 'Moored'
	elif ns == 6:
		legend = 'Aground!!'
	elif ns == 7:
		legend = 'Engaged in Fishing...'
	elif ns == 8:
		legend = 'Under way sailing'     
	elif ns == 9 or ns == 10 or ns == 11 or ns == 12 or ns == 13 or ns == 14 or ns == 15:
		legend = 'N/A'
	return legend



def messageType(ID):
	type = ''

	if ID == '000001':
		type = '01'
	elif ID == '000010':
		type = '02'
	elif ID == '000011':
		type = '03'
	elif ID == '000100':
		type = '04'
	elif ID == '000101':
		type = '05'
	elif ID == '000110':
		type = '06'
	elif ID == '000111':
		type = '07'
	elif ID == '001000':
		type = '08'
	elif ID == '001001':
		type = '09'
	elif ID == '001010':
		type = '10'
	elif ID == '001011':
		type = '11'
	elif ID == '001100':
		type = '12'
	elif ID == '001101':
		type = '13'
	elif ID == '001110':
		type = '14'
	elif ID == '001111':
		type = '15'
	elif ID == '010000':
		type = '16'
	elif ID == '010001':
		type = '17'
	elif ID == '010010':
		type = '18'
	elif ID == '010011':
		type = '19'
	elif ID == '010100':
		type = '20'
	elif ID == '010101':
		type = '21'
	elif ID == '010110':
		type = '22'
	elif ID == '010111':
		type = '23'
	elif ID == '011000':
		type = '24'
	else:
		type = 'fel brallor'
		
	return type



def Dd2DMm_x(magn):
	
	global crdnl_x
	global DEG_x
	global MINmin2_x

	crdnl_x = ''        
	Dd_x = 0
	DEG_x = 0
	MINmin2_x = 0
	DMn_x = []
	
	crdnl_x = magn[-1]                # Note the Cardinal sign
	Dd_x = float(magn[:-2])           # Just the figures, please
	DEG_x = int(Dd_x)                   # Keep the "floor"
	MINmin2_x = round((Dd_x - DEG_x) * 60, 2) # Get decimal Minutes
	
	MINminFull_x = round((Dd_x - DEG_x) * 60, 6)
	DMm_x = DEG_x, MINminFull_x, crdnl_x # Keep a string for reference
	
	return DMm_x


def Dd2DMm_y(magn):
	
	global crdnl_y
	global DEG_y
	global MINmin2_y

	crdnl_y = ''        
	Dd_y = 0
	DEG_y = 0
	MINmin2_y = 0
	DMn_y = []
	
	crdnl_y = magn[-1]                # Note the Cardinal sign
	Dd_y = float(magn[:-2])           # Just the figures, please
	DEG_y = int(Dd_y)                   # Keep the "floor"
	MINmin2_y = round((Dd_y - DEG_y) * 60, 2) # Get decimal Minutes
	
	MINminFull_y = round((Dd_y - DEG_y) * 60, 6)
	DMm_y = DEG_y, MINminFull_y, crdnl_y 
	
	return DMm_y



def typeCode2text(tc):
	''' Translates the Ship type code to it's text representation
	'''

	shipTypeDict = {34 : 'Diving ops' , 35 : 'Military ops' , 36 : 'Sailing' , 37 : 'Pleasure Craft' , 40 : 'High speed craft (HSC)' , 41 : 'HSC: Hazardous cat A' , 42 : 'HSC: Hazardous cat B' , 43 : 'HSC: Hazardous cat C' , 44 : 'HSC: Hazardous cat D' , 49 : 'HSC: No additional info' , 50 : 'Pilot Vessel' , 51 : 'Search & Rescue vessel' , 52 : 'Tug' , 53 : 'Port Tender' , 54 : 'Anti-pollution equipment' , 55 : 'Law Enforcement' , 60 : 'Passenger' , 61 : 'Passenger: Hazardous cat A' , 62 : 'Passenger: Hazardous cat B' , 63 : 'Passenger: Hazardous cat C' , 64 : 'Passenger: Hazardous cat D' , 69 : 'Passenger: No additional info' , 70 : 'Cargo' , 71 : 'Cargo: Hazardous cat A' , 72 : 'Cargo: Hazardous cat B' , 73 : 'Cargo: Hazardous cat C' , 74 : 'Cargo: Hazardous cat D' , 79 : 'Cargo: No additional info' , 80 : 'Tanker' , 81 : 'Tanker: Hazardous cat A' , 82 : 'Tanker: Hazardous cat B' , 83 : 'Tanker: Hazardous cat C' , 84 : 'Tanker: Hazardous cat D' , 89 : 'Tanker: No additional info' , 90 : 'Other Type' , 91 : 'Other Type: Hazardous cat A' , 92 : 'Other Type: Hazardous cat B' , 93 : 'Other Type: Hazardous cat C' , 94 : 'Other Type: Hazardous cat D' , 99 : 'Other Type: no additional info'}
	
	if tc in shipTypeDict:
			shipType_legend = shipTypeDict[tc]

	else:
		shipType_legend = 'N/A'
		
	return shipType_legend 



def getMonth(M):
	if M == 1:
		M = 'Jan'
	elif M == 2:
		M = 'Feb'
	elif M == 3:
		M = 'Mar'
	elif M == 4:
		M = 'Apr'
	elif M == 5:
		M = 'May'
	elif M == 6:
		M = 'Jun'
	elif M == 7:
		M = 'Jul'
	elif M == 8:
		M = 'Aug'
	elif M == 9:
		M = 'Sep'
	elif M == 10:
		M = 'Oct'
	elif M == 11:
		M = 'Nov'
	elif M == 12:
		M = 'Dec'
	else:
		M = 'N/A'
	return M
	

def getDay(D):
	if D == 0:
		D = 'N/A'

	return D

def get24h(H):
	if H == 24:
		H = 'N/A'
	else:
		H = '%0*d' % (2, H) ##################
	return H

def get60min(M):
	if M == 60:
		M = 'N/A'
	else:
		M = '%0*d' % (2, M) #################
	return M
	

def CommonNavigationBlock():
	'''Parses and interprets the information payload contained  
	in message types 1, 2 and 3.
	'''
	
	global _04_NavStatus
	global lastWord
	global popuTuple
	global oXY_ratio
	global spurio
	
	
# Chop up the message by data fields. 
# Then join the bitty sentence lists into proper bitstrings
	_01_MessageID = str2Bitstr(payLoad[:6])        # 6        uint
	_02_RepeatIndicator = str2Bitstr(payLoad[6:8]) # 2        uint
	_03_MMSI = str2Bitstr(payLoad[8:38])           # 30       uint
	_04_NavStatus = str2Bitstr(payLoad[38:42])     # 4        uint
	_05_ROT = str2Bitstr(payLoad[42:50])           # 8  int Signed!
	_06_SOG = str2Bitstr(payLoad[50:60])           # 10    udecimal
	_07_PositionAccuracy = str2Bitstr(payLoad[61]) # 1         uint
	_08_longitude = str2Bitstr(payLoad[61:89])     # 28 decimal Signed
	_09_latitude = str2Bitstr(payLoad[89:116])     # 27 decimal Signed
	_10_COG = str2Bitstr(payLoad[116:128])         # 12    udecimal
	_11_TrueHeading = str2Bitstr(payLoad[128:137]) # 9        uint
	_12_TimeStamp = str2Bitstr(payLoad[137:143])   # 6        uint
	_13_REST = payLoad[143:]                # Drop these bits for now!

	
	

# Decode each field's data appropriately
	oMessType = int(_01_MessageID , base=2)
	oRepIndex = int(_02_RepeatIndicator , base=2)
	oMMSI     = int(_03_MMSI , base=2)     #c.p. if len(_03_MMSI) <9 += ' '*(9-len(_03_MMSI)
	oStatus   = int(_04_NavStatus , base=2)
	oROT      = rot_2sC_Decoder( _05_ROT )
	oSOG      = sog_cog_BinValueDecoder(_06_SOG)
	oLati_Dd  = lat_2sC_Decoder(_09_latitude)  
	oLati_DMm = Dd2DMm_x(lat_2sC_Decoder(_09_latitude)) # Surplus variable eventually
	oLongi_Dd = lon_2sC_Decoder(_08_longitude)
	oLongi_DMm= Dd2DMm_y(lon_2sC_Decoder(_08_longitude)) # Surplus variable eventually
	oCOG      = sog_cog_BinValueDecoder(_10_COG)
	oHDG      = int(_11_TrueHeading , base=2) 
	oStamp    = int(_12_TimeStamp , base=2)
	oTypKnas  = spurio

# Reformat position coordinates for target range trigonometry
	if myOrigo[1] == 'S':
		myOrigoLati = '-' + myOrigo[0]
	else:
		myOrigoLati = myOrigo[0]
	if myOrigo[3] == 'W':
		myOrigoLongi = '-' + myOrigo[2]
	else:
		myOrigoLongi = myOrigo[2]
# Offsetting live gps coords for debugging/simulation purposes:		
	myOrigoLati =  float(myOrigoLati) - float(myOffset[0])
	myOrigoLongi =  float(myOrigoLongi) - float(myOffset[1])
	
	if oLati_Dd[-1] == 'S':
		lati_Dd = '-' + oLati_Dd[:-2]
	else:
		lati_Dd = oLati_Dd[:-2]
		
	if oLongi_Dd[-1] == 'W':
		longi_Dd = '-' + oLongi_Dd[:-2]
	else:
		longi_Dd = oLongi_Dd[:-2]

	oriLa	= float(myOrigoLati)
	oriLo	= float(myOrigoLongi)
	tarLa	= float(lati_Dd)
	tarLo	= float(longi_Dd)
	origo	= ((oriLa, 0, 0), (oriLo, 0, 0))
	target	= ((tarLa, 0, 0), (tarLo, 0, 0))	
	RnB     = rangeFinder(origo, target)
	oRange = RnB[0]
# Factor for plotting correct x-axis scale:	
	oXY_ratio = cos(radians(oriLa)) 

# Relative coordinates to target in equilateral XY-space
# i.e.(deltaX, deltaY) packed mainly for the sprite-blitting:
	oTarXY = (oXY_ratio * (tarLo - oriLo), tarLa - oriLa) 

# We unpack the coords again and fork a bearing computation here:
	oBearing =  findOurBearings(oTarXY[0], oTarXY[1])
	
# Zip a dict from the k- and v-lists
	valList1 = [
		systemClock,
		secondsUp, 
		oMMSI, 
		oStatus,
		statusCode2text(oStatus), # This substitutes navstatus_legend
		oROT, 
		oSOG, 
		oLati_Dd,
		oLati_DMm,
		oLongi_Dd,
		oLongi_DMm,
		oRange,
		oBearing,
		oTarXY,
		oCOG,
		oHDG,
		oStamp,
		oTypKnas]
		
	lastWord = dict(zip(keyList1, valList1))
	
	upDatePPL()
	popuWrite(popuList)



def BaseStationReport():
	'''Parses and interprets the information payload contained  
	in message type 4 Base Station Report.
	'''
	global lastWord
	global popuTuple
	global oXY_ratio
	global spurio

	_401_MessageID = str2Bitstr(payLoad[:6])
	_402_RepeatIndicator = str2Bitstr(payLoad[6:8]) 
	_403_MMSI = str2Bitstr(payLoad[8:38])
	_41_Yr = str2Bitstr(payLoad[38:52])
	_42_Mo = str2Bitstr(payLoad[52:56])
	_43_Day = str2Bitstr(payLoad[56:61])
	_44_Hr = str2Bitstr(payLoad[61:66])
	_45_Min = str2Bitstr(payLoad[66:72]) 
	_46_Sec = str2Bitstr(payLoad[72:78])
	_408_longitude = str2Bitstr(payLoad[79:107])
	_409_latitude = str2Bitstr(payLoad[107:134])
	
	oMessType = int(_401_MessageID , base=2)
	oMMSI     = int(_403_MMSI , base=2)
#	oYr       =			    # UTC, 1-999, 0 = N/A (default)
#	oMo       =
#	oDay      =
#	oHr       =
#	oMin      =
#	oSec      =			    # 0-59, 60=N/A
	oLati_Dd  = lat_2sC_Decoder(_409_latitude)  
	oLati_DMm = Dd2DMm_x(lat_2sC_Decoder(_409_latitude)) # Surplus variable eventually
	oLongi_Dd = lon_2sC_Decoder(_408_longitude)
	oLongi_DMm= Dd2DMm_y(lon_2sC_Decoder(_408_longitude)) # Surplus variable eventually
	oName     = 'Base Stn ' + str(oMMSI)
	oTypKnas  = spurio
	
# Reformat position coordinates for target range trigonometry
	if myOrigo[1] == 'S':
		myOrigoLati = '-' + myOrigo[0]
	else:
		myOrigoLati = myOrigo[0]		
	if myOrigo[3] == 'W':
		myOrigoLongi = '-' + myOrigo[2]
	else:
		myOrigoLongi = myOrigo[2]
# Offsetting live gps coords for debugging/simulation purposes:		
	myOrigoLati =  float(myOrigoLati) - float(myOffset[0])
	myOrigoLongi =  float(myOrigoLongi) - float(myOffset[1])
	
	if oLati_Dd[-1] == 'S':
		lati_Dd = '-' + oLati_Dd[:-2]
	else:
		lati_Dd = oLati_Dd[:-2]	
	if oLongi_Dd[-1] == 'W':
		longi_Dd = '-' + oLongi_Dd[:-2]
	else:
		longi_Dd = oLongi_Dd[:-2]

	oriLa	= float(myOrigoLati)
	oriLo	= float(myOrigoLongi)
	tarLa	= float(lati_Dd)
	tarLo	= float(longi_Dd)
	origo	= ((oriLa, 0, 0), (oriLo, 0, 0))
	target	= ((tarLa, 0, 0), (tarLo, 0, 0))	
	RnB     = rangeFinder(origo, target)
	oRange = RnB[0]
# Factor for plotting correct x-axis scale:	
	oXY_ratio = cos(radians(oriLa)) 
# Relative coordinates to target in equilateral XY-space
# i.e.(deltaX, deltaY) packed mainly for the sprite-blitting:
	oTarXY = (oXY_ratio * (tarLo - oriLo), tarLa - oriLa) 
# We unpack the coords again and fork a bearing computation here:
	oBearing =  findOurBearings(oTarXY[0], oTarXY[1])
	

# Zip a dict from the k- and v-lists
	valList4 = [
		systemClock,
		secondsUp, 
		oMMSI, 
		oName,
		oLati_Dd,
		oLati_DMm,
		oLongi_Dd,
		oLongi_DMm,
		oRange,
		oBearing,
		oTarXY,
		oTypKnas]

	lastWord = dict(zip(keyList4, valList4))
	
	upDatePPL()
	popuWrite(popuList)


def ShipTripData():
	'''Parses and interprets the information payload contained  
	in message type 5 (a multi-fragment sentence).
	'''
	
	global stashedPart
	global lastWord
	global popuTuple 
	
	multipLoad = stashedPart + payLoad
	
# Chop up the message by data fields. 
# Then join the bitty sentence lists into proper bitstrings.
	_501_MessageID = str2Bitstr(multipLoad [:6])      
	_502_RepeatIndicator = str2Bitstr(multipLoad [6:8]) 
	_503_MMSI = str2Bitstr(multipLoad [8:38])        
	_51_IMOnr = str2Bitstr(multipLoad [40:70])
	_52_CallSign = str2Bitstr(multipLoad [70:112])
	_53_ShipName = str2Bitstr(multipLoad [112:232])
	_54_ShipType = str2Bitstr(multipLoad [232:240])
	_55_DimBow = str2Bitstr(multipLoad [240:249])
	_55_DimStern = str2Bitstr(multipLoad [249:258])
	_56_DimPort = str2Bitstr(multipLoad [258:264])
	_56_DimStarb = str2Bitstr(multipLoad [264:270])
	_57_ETAmo = str2Bitstr(multipLoad [274:278])
	_57_ETAday = str2Bitstr(multipLoad [278:283])
	_57_ETAh = str2Bitstr(multipLoad [283:288])
	_57_ETAmin = str2Bitstr(multipLoad [288:294])
	_58_Destination = str2Bitstr(multipLoad [302:422])
	
	
	
# Decode each field's data appropriately
	oMessType = int(_501_MessageID , base=2)
	oMMSI     = int(_503_MMSI , base=2) #c.p. if len(_03_MMSI) <9 += ' '*(9-len(_03_MMSI)
	oIMO      = int(_51_IMOnr , base=2)
	oCallOut  = str.rstrip(sixBit2ICAO(_52_CallSign))	# 7 six-bits chars
	oCallSign = str.rstrip(sixBit2ASCIIchar(_52_CallSign))
	oName     = str.rstrip(sixBit2ASCIIchar(_53_ShipName))    # 20 six-bits chars
	oType     = typeCode2text(int(_54_ShipType , base=2)) # 0-99
	oBow      = int(_55_DimBow , base=2)
	oStern    = int(_55_DimStern , base=2)  
	oLOA      = oBow + oStern
	oPort     = int(_56_DimPort , base=2)
	oStarb    = int(_56_DimStarb , base=2)
	oBeam     = oPort + oStarb
	oETAmo    = getMonth(int(_57_ETAmo, base=2))   # 1-12, 0=N/A
	oETAday   = getDay(int(_57_ETAday, base=2))    # 1-31, 0=N/A
	oETAh     = get24h(int(_57_ETAh, base=2))      # 0-23, 24=N/A
	oETAmin   = get60min(int(_57_ETAmin, base=2))  # 0-59, 60=N/A
	oDest     = sixBit2ASCIIchar(_58_Destination)   # 20 six-bits chars

# Zip a dict from the k- and v-lists
	valList5 = [
		systemClock,
		secondsUp,
		oMMSI,  
		oIMO,
		oCallOut,
		oCallSign,
		oName,
		oType,
		oLOA,
		oBeam,
		oETAmo,
		oETAday,
		oETAh,
		oETAmin,
		oDest,]
		
	lastWord = dict(zip(keyList5, valList5))
	
	upDatePPL()
	popuWrite(popuList)

	
def fPrint(nr):
	'''
	Auxillary routines for watching the input stream, including any skipped 
	messages (i e those message types that we don't care about: All types 
	except 1 to 5)
	'''
	global ticker
	global idBits
	
	if nr == 1:
		print '\n_____________ Nummer ', ticker,'_____________'
	if nr == 2:
		print '\n::::::::::::::::::::::'
		print 'This message type (',idBits,') is not implemented yet! '
		print   '::::::::::::::::::::::'
	if nr == 3:
		print '\n This is a type ',idBits,' message with partsCount > 2 !'
		print 'Can\'t handle those, can we.'
	if nr == 4:
		print '\n::::::::::::::::::::::'
		print 'Here we ignore a two-part message of type',idBits,'.'
		print 'Jumping one tick...'
		print '::::::::::::::::::::::'
		


def recalculate_coordinate(val,  as_= None):
	'''
	Accepts a coordinate as a tuple (degree, minutes, seconds). 
	You can give only one of them (e.g. only minutes as a floating
	point number) and it will be duly recalculated into degrees,
	minutes and seconds.
	Return value can be specified as 'deg', 'min' or 'sec'; 
	default return value is a proper coordinate tuple.
	'''
	
	deg,  min,  sec = val
	# pass outstanding values from right to left
	min = (min or 0) + int(sec) / 60
	sec = sec % 60
	deg = (deg or 0) + int(min) / 60
	min = min % 60
	# pass decimal part from left to right
	dfrac,  dint = modf(deg)
	min = min + dfrac * 60
	deg = dint
	mfrac,  mint = modf(min)
	sec = sec + mfrac * 60
	min = mint
	if as_:
		sec = sec + min * 60 + deg * 3600
		if as_ == 'sec': return sec
		if as_ == 'min': return sec / 60
		if as_ == 'deg': return sec / 3600
	return deg,  min,  sec


def rangeFinder(here, thar):
	'''
	Calculate distance (in nautical miles) between two points 
	given as (lat, long) pairs based on the Haversine formula 
	(http://en.wikipedia.org/wiki/Haversine_formula). 
	Implementation inspired by JavaScript implementation from 
	http://www.movable-type.co.uk/scripts/latlong.html. Accepts 
	coordinates as tuples (deg, min, sec), but coords can be given
	in any form - e.g. specified in minutes: (0, 3133.9333, 0)
	is interpreted as (52.0, 13.0, 55.998000000008687).
	'''
	nmf = 3440.065  # Nautical miles factor

	here_latt = radians(recalculate_coordinate(here[0],  'deg'))
	here_long = radians(recalculate_coordinate(here[1],  'deg'))
	thar_latt = radians(recalculate_coordinate(thar[0],  'deg'))
	thar_long = radians(recalculate_coordinate(thar[1],  'deg'))
	d_latt = thar_latt - here_latt
	d_long = thar_long - here_long
	a = sin(d_latt/2)**2 + cos(here_latt) * cos(thar_latt) * sin(d_long/2)**2
	c = 2 * atan2(sqrt(a),  sqrt(1-a))
	
	return nmf * c, nmf * d_latt
				


def findOurBearings(deltaX, deltaY):
	
	x_ = abs(deltaX)
	y_ = abs(deltaY)
	boring = 0.0

	if deltaX > 0 and deltaY >= 0:
	# target is in quadrant I (x_+ y_+)
	# Make sure never to divide by 0.
		if y_ > 0 and x_ > 0:
			aRad = atan(x_/y_)
			aDeg = (aRad/pi)*180
			boring = float(aDeg)
		elif x_ == 0:
			boring = 90.0
		else:
			boring = 0.0
	
	elif deltaX >= 0 and deltaY < 0:
	# target is in quadrant II (x_+ y_-)
		if y_ > 0 and x_ > 0:
			aRad = atan(y_/x_)
			aDeg = (aRad/pi)*180
			boring = float(aDeg) + 90 ##
		elif x_ == 0:
			boring = 270.0
		else:
			boring = 0.0

	elif deltaX < 0 and deltaY < 0:
	# target is in quadrant III (x_- y_-)
		if y_ > 0 and x_ > 0:
			aRad = atan(x_/y_)
			aDeg = (aRad/pi)*180
			boring = float(aDeg) + 180
		elif y_ == 0:
			boring = 180.0
		else:
			boring = 270.0

	else:
	# target is in quadrant IV (x_- y_+)
		if y_ > 0 and x_ > 0:
			aRad = atan(y_/x_)
			aDeg = (aRad/pi)*180
			boring = float(aDeg) + 270 ##
		elif x_ == 0:
			boring = 90.0
		else:
			boring = 180.0 
		
	return str(int(round(boring)))

def upDatePPL():
	global popuList
	global lastWord

	newMMSI = lastWord['k0_MMSI']

	pointer = search(popuList, newMMSI)
	
	if pointer != 1000:
		for field in lastWord:
			popuList[pointer][field]=lastWord[field]
		popuList.append(popuList[pointer])
		del popuList[pointer]
	else:
		popuList.append(lastWord)		
	del lastWord

def search(db, val, k0 ='k0_MMSI'):
	for i in range(len(db)):
		if db[i].has_key(k0):
			if val == db[i][k0]:
				break	
			else:
				i = 1000
		else:
			pass
	return i
		
def popuWrite(pList):
	''' Dynamically updates a comma-separated file with selected
	values from the "shipfile" dicts '''
	
	global secondsUp
	global obsodelete

	dummy = ['000000000,','INIT DUMMY,',',',',',',',',',',',',',',',\
	'360,',',',',',',',',','1.0,','0,',',',',',',',',','1,','ok','\n']
	
	if os.path.isfile('./data/census.csv'):
		line = [] # We initialise an empty list to have something to append to.
	else:	# The dummy line provides some minimum contents, in the odd case a brand new census-file needs to be created.
		# Unfortunately, the non-existing target will then stay blitted to the plotter's origo for the entire session...
		line = dummy 	
	csvf = open('./data/census.csv','wb')	

	for shipfile in pList:
		diffy = int(secondsUp) - int(shipfile['k0_SECONDS'])
		if diffy > 300:    # This value equals the minimum number of seconds of non-activity before annihilation! 
			obsodelete = True			

		if shipfile.has_key('k1_LAT_Dd'):	
		# This diverts targets that lack LAT, LON, SOG, COG, HDG, ROT, etc, pending
		# their presumed completion. Now, if the session's first dict from popuList
		# contains only mess-type 5 data, i.e. has no 'k1_LAT_Dd' key etc, the 
		# resulting empty list of the census-file will crash PloyPlotter.
		# Update: We seem to have solved this more-or-less by some ungraceful 
		# exception juggling in PloyPlot's while-loop.
			if shipfile.has_key('k0_MMSI'):
				line.append( str(shipfile['k0_MMSI']) + ',')	# 0
			else:
				continue			# NEW
			if shipfile.has_key('k5_NAME'):
				line.append( shipfile['k5_NAME'] + ',')	# 1
			else:
				line.append(',')
			if shipfile.has_key('k5_CALLPHONO'):
				line.append( shipfile['k5_CALLPHONO'] + ',')	# 2
			else:
				line.append(',')
			if shipfile.has_key('k5_CALLSIGN'):
				line.append( shipfile['k5_CALLSIGN'] + ',')	# 3
			else:
				line.append(',')
			if shipfile.has_key('k1_NAVSTATUS'):
				line.append( shipfile['k1_NAVLEGEND'] + ',')	# 4 Note key change
			else:
				line.append(',')
			if shipfile.has_key('k5_TYPE'):
				line.append( shipfile['k5_TYPE'] + ',')	# 5
			else:
				line.append(',')
			if shipfile.has_key('k5_LOA'):
				line.append( str(shipfile['k5_LOA']) + ',')	# 6
			else:
				line.append(',')
			if shipfile.has_key('k5_BEAM'):
				line.append( str(shipfile['k5_BEAM']) + ',')	# 7
			else:
				line.append(',')
			if shipfile.has_key('k1_SOG'):
				line.append( shipfile['k1_SOG'] + ',')	# 8
			else:
				line.append(',')
			if shipfile.has_key('k1_COG'):
				line.append( shipfile['k1_COG'] + ',')	# 9
			else:
				line.append('360,')	# Just to prevent hiccups in the plotter
			if shipfile.has_key('k1_HDG'):
				line.append( str(shipfile['k1_HDG']) + ',')	#10
			else:
				line.append(',')
			if shipfile.has_key('k1_ROT'):
				line.append( shipfile['k1_ROT'] + ',')	#11
			else:
				line.append(',')
			if shipfile.has_key('k1_LAT_Dd'):
				line.append( shipfile['k1_LAT_Dd'] + ',')	#12
			else:
				line.append(',')
			if shipfile.has_key('k1_LON_Dd'):
				line.append( shipfile['k1_LON_Dd'] + ',')	#13
			else:
				line.append(',')
			if shipfile.has_key('k1_RANGE'):  # How do you like this little gem?: 
				line.append(str(Decimal(str(round(shipfile['k1_RANGE'],2))).quantize(Decimal('0.01'))) + ',')	#14
			else:
				line.append(',')
			if shipfile.has_key('k1_BEARING'):
				line.append(str(shipfile['k1_BEARING']  + ','))	#15
			else:
				line.append(',')
			if shipfile.has_key('k1_XYRELATION'):
				line.append(str(shipfile['k1_XYRELATION'][0])  + ',')   #16 Relative coordinate X to target
			else:
				line.append(',')
			if shipfile.has_key('k1_XYRELATION'):
				line.append(str(shipfile['k1_XYRELATION'][1])  + ',')   #17 Relative coordinate Y to target
			else:
				line.append(',')
			if shipfile.has_key('k5_DESTINAT'):
				line.append( str.strip(shipfile['k5_DESTINAT']) + ',')	#18
			else:
				line.append(',')
			if shipfile.has_key('k0_SYSTEMCLOCK'):
				line.append(str( shipfile['k0_SYSTEMCLOCK']) + ',')	#19
			else:
				line.append(',')
			if shipfile.has_key('k0_SECONDS'):
				line.append( shipfile['k0_SECONDS'] + ',')	#20
			else:
				line.append(',')
			if shipfile.has_key('k0_TRUBBEL'):
				line.append (str( shipfile['k0_TRUBBEL'] )) #21 Default corruption flag. This could be either 'ok' or an error id.
			else:
				line.append('dunno') # This is a third possible flag value, strictly speaking.

			line.append('\n')
		else:
			pass

		
	csvf.writelines(line)
	csvf.close()


## ------------ Comment out the following three defs in static origo mode --------------
## ------------ Comment out the following four defs in simulation mode -----------------


def findOrigo():       # simple "loop-and-try-again"
	
	retry = True
	while retry:
		line = []
		line = ser.readline()
		tmpOrigo = parseGPS(line.split(','))
		if tmpOrigo[4] == 1:      # It's a GPRWC type of message!
			origo = tmpOrigo
			retry = False       
	return origo
		
	
	
def parseGPS(lina):
	'''Processes NMEA 0183 formatted GPS position data (DD:MM.mm).
	Returns a tuple of latitude, longitude (DD.dd), and a $GP type confirmation flag. 
	'''

	latitude  	= 0.0
	NS 		= ''
	longitude 	= 0.0
	EW 		= ''

	if lina[0] == '$GPRMC':
		try:
			RMC = 1
			latitude = float(lina[3][0:2]) + (float(lina[3][2:])/60.0)
			NS = lina[4]
			longitude = float(lina[5][0:3]) + (float(lina[5][3:])/60.0)
			EW = lina[6]
		except ValueError:
			RMC = 0
			latitude = 0
			NS = 0
			longitude = 0
			EW = 0
			print "GPS ValueError!"
		except IndexError:
			RMC = 0
			latitude = 0
			NS = 0
			longitude = 0
			EW = 0
			print "GPS IndexError!"
		
	else:
		RMC = 0
		latitude = 0
		NS = 0
		longitude = 0
		EW = 0

	return latitude, NS, longitude, EW, RMC


def portScanUSB():
	usbport = '/dev/ttyUSB'
	found = False
	eureka = ''
	for i in range(64):
		if found == False:    # This will return only the port found first
			try:
				ser = serial.Serial(usbport + str(i))
				ser.close()
				print 'Found ttyUSB', i, ' (a.k.a. COM', i + 1, ')'
				eureka = usbport + str(i) 
				found = True
			except serial.serialutil.SerialException:
				pass
	if not found:
		print 'No ports found. Make sure the GPS sensor is connected, etc.'
	return eureka

## ------------ Comment out the preceding three defs in static origo mode --------------

def flushLog(filename):
	'''Zap all contents in file filename'''
	
# This function empties the file AISMon.log in an attempt to always keep it small, but 
# it seems AISMon.exe writes its complete buffer back to its logfile for each sync.
# The simple way to empty the buffer and stop the logfile growing very large is to 
# occasionally cycle the "Stop/Start monitoring" button in AISMons control window.

	nulline = '\x00'
	try:
		log = open(filename,'w+')
		try:
			log.write(nulline)  # write an empty string
		finally:
			log.close()
	except IOError:
		print 'Can\'t find or open "AISMon.log" for zapping (IOError)'
		pass
		
## ------------ Comment out the preceding four defs in simulation mode -----------------


# ##################################################################
# ------------------ Global Vars and Constants ---------------------
# ##################################################################

# The following dict returns the complement of a single bit.
# (Simpler than a function based on an if-else test...)
# Works for ASCII and numeric!
# A binary point/period is its own "complement", for convenience:
bitComplement = { '0':'1', '1':'0',  0:1, 1:0 , '.':'.' }

partsCount = []
partNumber = []
sequentID = []
payLoad = []
stashedPart = []
stashedSequentID = [] 
_04_NavStatus = []
navstatus_legend = []
popuList = [{},]
keyList1 = ['k0_SYSTEMCLOCK', 'k0_SECONDS', 'k0_MMSI','k1_NAVSTATUS','k1_NAVLEGEND',
'k1_ROT','k1_SOG','k1_LAT_Dd','k1_LAT_D_Mm','k1_LON_Dd','k1_LON_D_Mm',
'k1_RANGE','k1_BEARING','k1_XYRELATION','k1_COG','k1_HDG','k1_TIMESTAMP','k0_TRUBBEL']  ## 18 items
keyList4 = ['k0_SYSTEMCLOCK', 'k0_SECONDS','k0_MMSI','k5_NAME','k1_LAT_Dd','k1_LAT_D_Mm',
'k1_LON_Dd','k1_LON_D_Mm','k1_RANGE','k1_BEARING','k1_XYRELATION','k0_TRUBBEL']  ## 12 items
keyList5 = ['k0_SYSTEMCLOCK', 'k0_SECONDS','k0_MMSI','k5_IMO','k5_CALLPHONO',
'k5_CALLSIGN','k5_NAME','k5_TYPE','k5_LOA','k5_BEAM','k5_ETA_Mo','k5_ETA_Dy',
'k5_ETA_Hr','k5_ETA_Mi','k5_DESTINAT']  ## 15 items
valList = []
oXY_ratio = []
lastWord = {}
spurio = 'ok'  # Error code flag reset. (Valid IDs: # 01 == Lat out of bounds, 02 == Ditto for Lon)
inputt = ''
idBits = ''
ticker = 0
systemClock = ''
nillString = ''
foundPort = ''
obsodelete = False  # Ripe-for-deletion flag.
timeOutTime = 0   # Ticker to trigger the sweep-up. Used to set the frequency of one-shot deletions.
myOrigo = ()  # This var is either set with myPosGPS or updated by the live GPS input
fSize = 0



# ##################################################################
# ----------------------- Static dummy vars ------------------------
# ##################################################################


	## Select a data input file for use in simulation modes
#ipf = './data/aivdm/AIS_UK_2000_lines.txt'
#ipf = './data/aivdm/AISMon_Sandhamn_med_Wappen_110729.log'

	## Use the AISMon log file for AIS input in real-time! 
#ipf = './data/aivdm/LinktoAISMon.log'
ipf = '/home/xneb/.wine/drive_c/Program Files/AISMon/AISMon.log'


	## Static Position definition, lacking GPS input (substitute your actual position) 
#myPosGPS = staticPos232 = ('59.463333', 'N', '18.05', 'E') # (Decimal degrees)
#myPosGPS = staticPosSandhamnsBoj = ('59.28351', 'N', '18.925208', 'E')

	## The myOffset constant is useful for simulation and debugging with GPS input. 
	## Defaults to nil:                                                             
myOffset = (0, 0)				  	#cp myPosGPS = ('59.463333', 'N', '18.05', 'E')
#myOffset = (8.671666, 19.163889)	#cp myPosPmouth= ('50.791667', 'N', '1.113889', 'W')
#myOffset=...					  	#cp myPosLA = ('33.741667', 'N', '118.225', 'W')



# ##################################################################
# ------------------------- Init routines---------------------------
# ##################################################################


	## Start the wxPython GUI already 
child1 = subprocess.Popen('./AISflukt/AISflukt.py')
time.sleep(0.5)

	## Start the Pygame GUI "Radar Plotter"
child2 = subprocess.Popen('./Ployplot.py')

## ------------ Comment out the following lines in static origo mode --------------

	## Identify, open and prime the serial port used by the GPS dongle
foundPort = str(portScanUSB())
ser = serial.Serial(foundPort, 4800, timeout=1)
ser.baudrate = 4800 		# Is this redundant?
ggr = 0
while ggr < 4:
	ggr = ggr + 1
	ser.readline()
	time.sleep(0.25)

## ------------ Comment out the preceding lines in static origo mode --------------


	## Pyglet stuff -- Forge a window to end them all!
funster = ww.Window(width = 400, height = 55, caption = 'PupAIS')
x, y = funster.get_location()
funster.set_location(x - 5, y + 475)
blue = (0,0,0.5,1)
gl.glClearColor(*blue)
label = tt.Label('PupAIS is now running headless in the background. 	\n\
Please close this window to kill the associated\n\
processes in an orderly way -- zombies and all!',
font_name = 'Lucida Sans Typewriter',
font_size = 8,
color = (255,255,255,255), 
x = funster.width//2, y = funster.height//2,
anchor_x = 'center', anchor_y = 'center',
multiline = True,
width = 380)
pic = image.load('./data/pngs/popeye_smallest.png')		
pic.anchor_x = -315
pic.anchor_y = 90

# ##################################################################
# -------------------------- Main loop -----------------------------
# ##################################################################

while not funster.has_exit: # State of the Pyglet window controls the main loop
	funster.dispatch_events()
	funster.clear()	
	label.draw()
	pic.blit(x, y)
	funster.flip()
	
	f = file(ipf)   # (Re-)establish the input file object
	fSize = os.path.getsize(ipf)  # Test whether input file has any (new) contents
	while fSize > 0:			  # See note in def flushLog()
		print "Sync #", ticker, "  (fSize is now:", fSize,")"
		inputt = f.readline() 
		if len(inputt) == 0: # Nothing left to read: Delete all lines and reload
			print "Now flushing" 
			f.close()
			flushLog(ipf)	## Comment this line out in simulation modes
			time.sleep(1)	# No need to haste... Let's idle awhile
			f = file(ipf) 	# We must not forget to open the flushed input file again
			break
		if len(inputt) <= 4 and str('\n') in inputt: # Empty lines in file?
			ticker = ticker + 1
			continue
		try:
			data, cksum, calc_cksum = checkSumCheck(inputt)  # Does it check out?
		except ValueError:
			break
		if cksum != calc_cksum:
			print 'Error in checksum for: %s' % (data)
			break
		else:		    ##     At last we can go to work!     
			ticker = ticker + 1
			systemClock = time.strftime('%H:%M:%S',time.localtime())
			secondsUp = str(3600*int(systemClock[:2])+60*int(systemClock[3:5])+int(systemClock[6:]))
			partsCount, partNumber, sequentID, payLoad = decapsulate(inputt)
			idBits = messageType(str2Bitstr(payLoad [:6]))
			myOrigo = findOrigo() ## If using live GPS input
#			myOrigo = myPosGPS     ## If using static coordinates
			if partsCount == '1':
	#				fPrint(1)
				if idBits == '01' :
					CommonNavigationBlock()
				elif idBits == '02' :
					CommonNavigationBlock()
				elif idBits == '03' :
					CommonNavigationBlock()
				elif idBits == '04' :
					BaseStationReport()
				else:
	#				fPrint(2)   
					pass     # No significance to us, so just ignore it...
			elif partsCount == '2':
				if idBits == '05':
					if partNumber == '1':
						stashedPart = payLoad
						stashedSequentID = sequentID
				else:
					if stashedSequentID == sequentID:
	#					fPrint(1)
						ShipTripData()
					else:
						if idBits != '01':
	#						fPrint(1)
	#						fPrint(4)
							pass
						else:
							continue
			else:
	#			fPrint(1)
	#			fPrint(3)
				pass
		if timeOutTime > 112: # Another half-minute has passed (approx in non-idling state). Time to sweep up.
	#		print '+++++++++    Here we go again @', ticker
			if obsodelete == True:
				print 'Deleting', popuList[0]['k0_MMSI'], ', not blipped since ',popuList[0]['k0_SYSTEMCLOCK']
				del popuList[0]# This now reduces the list-length for both \
								# PopuLister and PloyPlotter!
				obsodelete = False
			timeOutTime = 0
		timeOutTime += 1
		time.sleep(.25)   # A loop delay is needed for termination (?). Also for the correct timeOutTime time-scale!
	print "idling..."
	time.sleep(1)
child2.terminate()
child1.terminate()
f.close() 
print "                 Bye-bye Superfly!"
