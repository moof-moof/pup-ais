#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Filename: PloyPlot.py

__version__ = '$Revision: 4.3 $'
__date__ = '$Date: 2011-05-29 $'
__author__ = 'Martin Bergman'
__doc__ = '''

-------------------------------------------------------------------
PloyPlot is a 2D plotter interface for the AIS NMEA string parser 
PupAIS. It reads plain text data from a repeatedly updated comma
separated "census" file, then populates a pseudo radar screen with 
sprites for all blips/targets.
-------------------------------------------------------------------

@author: U{'''+__author__+'''<http://goto.glocalnet.net/mabe/>}
@version: ''' + __version__ +'''                                   
@status: under development
@license: GPL
'''


from pygame import *
from random import randint
import csv
import os

## Use this line for regular screen sizes:
#os.environ['SDL_VIDEO_WINDOW_POS'] = str(610) + ',' + str(0)#str(48)
## Use this for small screens:
os.environ['SDL_VIDEO_WINDOW_POS'] = str(415) + ',' + str(0)#str(48)
init()



def main():   
## Functions                                        
        def load_image(name):
                img = image.load(name)
                img = img.convert()
                return img, img.get_rect()

        def render_calls_label(text, position):
                fg = 220, 0, 100 # dark red
                bg = 255, 255, 0 # yellow
                typ = './data/fonts/LucidaTypewriterRegular.ttf' 
                ffont = font.Font(typ, 9)
                size = ffont.size(text)
                format =  text 
                ren = ffont.render(format, 0, fg, bg)
                label = screen.blit(ren, position)
                return label 
        
        def render_mmsi_label(text, position):
                fg = 220, 0, 100
                typ = './data/fonts/LucidaTypewriterRegular.ttf'
                ffont = font.Font(typ, 9)
                size = ffont.size(text)
                format = '>' + text + ' '
                ren = ffont.render(format, 0, fg)
                label = screen.blit(ren, position)
                return label     
        
        def render_scale(text, position):
                fg = 255,255,255
                bg = 0,0,0
                typ = './data/fonts/LucidaTypewriterBold.ttf' 
                ffont = font.Font(typ, 11)
                size = ffont.size(text)
                format = text
                ren = ffont.render(format, 0, fg)
                label = screen.blit(ren, position)
                return label
        
        def dpi_scaled(floatsome, zoooom):
                return int(floatsome * 15000 / zoooom) # 15000 => ca 250px/NM            
        
        def search(pops, val, k ='mmsi'):
                for i in range(len(pops)):
                        if pops[i].has_key(k):
                                if val == pops[i][k]:
                                        break	
                                else:
                                        i = 1000
                        else:
                                pass
                return i        

        def elp():
                halt = True
                screen.blit(helpscreen, (0, 0))
                display.update()
                while halt == True:
                        for e in event.get():
                                if e.type == KEYDOWN:
                                        if e.key == K_n:
                                                go_on = screen.blit(background, (0, 0))
                                                halt = False
                return go_on
                                
                
 ## Variables                                        

        zoom = 16.0     # Default chart scale (Nautical Miles of outer ring radius)
        deelay = 1000  # A second seems-about-right
        done = False
        origo = (300,270)    # This is where we are -- always! ##<<<< 300,300 
        targs = list(100*[{},]) # Ready-made list stub for filling in the positional data to \
                                # draw each target's sprite representation.
        alfa = list(100*[0,])     # Intermediate variables for angular values.
        posi = list(100*[0,])  # Intermediate variables for rectangular values.
        pops = [{}]   # The semi-permanent "population list", safekeeping an increasing \ 
                # number of unsorted target dicts, whose discreet values (mmmsi, name, calls,\
                # sog, cog, xrel, yrel) are updated with every census read.
        purge_ticker = 0 # Meters the time to occasional pops purge-and-rebuilds.
        

## Set up the window                                 

        screen = display.set_mode((600, 550)) ##<<<< Substitute 600, 615 for big screens
        background = image.load('./data/pngs/radar02_600px90dpi.png')
        bline = image.load('./data/pngs/bottomline.png')
        splash = image.load('./data/pngs/greatE.png')
        helpscreen = image.load('./data/pngs/Help_Screen.png')
        display.set_caption('PloyPlotter (PupAIS for small screen)')
        screen.blit(splash, (0, 0))     # We begin with a splash...
        mouse.set_visible(True)

## Set up the sprites                                

        tailpic, trect = load_image('./data/pngs/targTailAA.png')
        tailpic = tailpic.convert()
        colorkey = tailpic.get_at((0,0))
        tailpic.set_colorkey(colorkey)
        
        tailnope, nrect = load_image('./data/pngs/targTailNope.png')
        tailnope= tailnope.convert()
        colorkey = tailnope.get_at((0,0))
        tailnope.set_colorkey(colorkey)

        spotpic, srect = load_image('./data/pngs/targSprite_Vit.png')
        srectCenterX, srectCenterY  = srect[2]/2, srect[3]/2
        spotpic = spotpic.convert()
        colorkey = spotpic.get_at((0,0))
        spotpic.set_colorkey(colorkey)

        focuspic, frect = load_image('./data/pngs/targSprite_Svart.png')
        frectCenterX, frectCenterY  = frect[2]/2, frect[3]/2
        focuspic = focuspic.convert()
        colorkey = focuspic.get_at((0,0))
        focuspic.set_colorkey(colorkey)
        
        basepic, brect = load_image('./data/pngs/targBaseStn.png')
        brectCenterX, brectCenterY  = brect[2]/2, brect[3]/2
        basepic = basepic.convert()
        colorkey = basepic.get_at((0,0))
        basepic.set_colorkey(colorkey)

## On your marks!

        display.update()
        time.delay(deelay*4)  # Hold the splash screen up for awhile

## Do da Loop                                        

        while done == False: 
                purge_ticker += 1
                screen.blit(background, (0, 0))
                
                reader = csv.reader(open('./data/census.csv', 'rb'))
                
                for row in reader:
                        try:
                                tgt = {'mmsi':row[0],'name':row[1],'calls':row[3],
                                'sog':row[8],'cog':row[9],'xrel':row[16],'yrel':row[17]}
                        except IndexError: 
                                continue  # ("Break" statement almost works)
                        if pops[0] == {}: # This would be the init/purged state dummy dict
                                pops.append(tgt)
                                del pops[0]
                        else:
                                pointer = search(pops, tgt['mmsi'])
                                if pointer != 1000:
                                        for field in tgt:
                                                pops[pointer][field] = tgt[field]
                                        pops.append(pops[pointer])
                                        del pops[pointer] 
                                else: # We have a new blip
                                        pops.append(tgt) 
                        del tgt

                nr = 0 
                for tg in pops:
## First we deal with the target's orientation (COG)
                        try:
                                if tg['cog'] == '0':  # (This used to complain if we didn't \
                                                        # provide an "init dummy" target with \
                                                        # fake COG value. But see below.)
                                        alfa[nr] = float(0)
                                        rotatedTail = transform.rotate(tailnope, alfa[nr])
                                elif tg['cog'] == '360':
                                        alfa[nr] = float(0)
                                        rotatedTail = transform.rotate(tailnope, alfa[nr])
                                else:
                                        alfa[nr] = float(tg['cog']) * (-1) # Mirrored angles
                                        rotatedTail = transform.rotate(tailpic, alfa[nr])
## Now for the target's position relative to us:
                                try:
                                        posi[nr] = dpi_scaled(float(pops[nr]['xrel']),zoom),dpi_scaled(float(pops[nr]['yrel']),zoom)
                                except ValueError: # Null error pseudo-fix:
                                        posi[nr] = dpi_scaled(float(0),zoom),dpi_scaled(float(0),zoom) 
                        except KeyError: # This opt-out partly solved the "no COG" crashes. 
                                          # No need for an "init dummy":
                                break 
## Time to blit the blips:
                        rotatedTailCenter = rotatedTail.get_rect()
                        trectCenterX = rotatedTailCenter[2]/2
                        trectCenterY = rotatedTailCenter[3]/2
                        targs[nr] = {  'Xt': 300 + posi[nr][0] - trectCenterX, 
                                        'Yt': 270 - posi[nr][1] - trectCenterY, ####
                                        'Xs': 300 + posi[nr][0] - srectCenterX, 
                                        'Ys': 270 - posi[nr][1] - srectCenterY, ####
                                        'r':   rotatedTail  }
                                        
                        if str(pops[nr]['name']).startswith('Base'):# Mess type 4 needs no tail!
                                screen.blit(basepic, (targs[nr]['Xs'], targs[nr]['Ys']))
                        else:
                                screen.blit(targs[nr]['r'], (targs[nr]['Xt'], targs[nr]['Yt']))
                                if nr == len(pops)-1:   # Shine a Black Spotlight on da Mover!
                                        screen.blit(focuspic, (targs[nr]['Xs'], targs[nr]['Ys']))
                                else:                   # Plain white pop-eyes for the rest
                                        screen.blit(spotpic, (targs[nr]['Xs'], targs[nr]['Ys']))
## Finally, we tack a unique label to the sprite:
                        mummy = str(pops[nr]['mmsi'])
                        if str(pops[nr]['calls']) != '': # Show the Callsign if we have it
                                render_calls_label(pops[nr]['calls'], (targs[nr]['Xs']+20, targs[nr]['Ys']+20))
                        else:                           # Substitute an MMSI abbreviation
                                render_mmsi_label(mummy[-4:], (targs[nr]['Xs']+20, targs[nr]['Ys']+20))
                        nr += 1
## We blit the bottomline last, so as not to be trod upon by galoping sprites:
                screen.blit(bline, (0, 535))  ##<<<< 600
                try:
                        render_scale('ZOOM: %s Nm | TARGETS: %s | FOCUS: %s | UP: North  |    "H" for Help'\
                        %(str(zoom),len(pops),pops[len(pops)-1]['mmsi']),(10,535))##<<<< 600
                except KeyError: # This simple exception handler seems to have solved the \
                                # "no mmsi" crashes, for now. Thus again, an "init dummy" \
                                # solution in PupAIS.popuWrite() is no longer necessary:
                        render_scale('ZOOM: %s Nm | TARGETS: %s | FOCUS: %s | UP: North  |    "H" for Help'\
                        %(str(zoom),len(pops),'--------'),(10,535))##<<<< 600
                        
                display.update()
                if purge_ticker >= randint(55,80):
                        pops = [{}] # We could purge the pops dictlist in each loop, \
                        # instantly omitting any "obsodeleted" targets, but also \
                        # causing frequent read/write clashes and blank loops...\
                        # To minimise collision risk we purge only once per ~60 loops.
                        purge_ticker = 0
                time.delay(deelay) 
                for e in event.get():
                        if e.type == QUIT:
                                done = True
                        elif e.type == KEYDOWN:
                                if e.key == K_UP:  # Double the scale
                                        zoom = zoom * 2
                                elif e.key == K_DOWN:  # Half scale
                                        zoom = zoom / 2
                                elif e.key == K_h: # Show the Help screen
                                        elp()
                                elif e.key == K_ESCAPE:
                                        done = True
if __name__ == '__main__': main()
quit ()
