#!/usr/bin/python
# -*- coding: utf-8 -*-
# Filename: AISflukt.py

__version__ = '$Revision: 4.4 $'
__date__ = '$Date: 2011-01-14 $'
__author__ = 'Martin Bergman'
__doc__ = '''

-------------------------------------------------------------------
PopuLister is a GUI interface for the AIS NMEA string parser PupAIS. 
It reads plain text data from a repeatedly updated comma separated 
"census" file, sorts and lists the existing population of targets, 
and exhibits available properties of individual targets using one 
"card" per target.
-------------------------------------------------------------------

@author: U{'''+__author__+'''<http://goto.glocalnet.net/mabe/>}
@version: ''' + __version__ +'''
@status: under development
@license: GPL
'''

from PythonCard import dialog, model, timer
import time

 ## Variables                                        

datafile = '../data/census.csv'
selektion = 0
columns = [ 'mmsi',
            'name',
            'phono',
            'calls',
            'navs',
            'vtype',
            'LOA',
            'beam',
            'SOG',
            'COG',
            'HDG',
            'ROT',
            'LAT',
            'LON',
            'proxim',
            'bear',
            'tarXpx',
            'tarYpx',
            'dest',
            'clck',
            'secs',
            'oops']
        
## Functions                                        

def sortByRange(a,b):   # Closer targets go to the top of the list
        try:
                if float(a['proxim']) > float(b['proxim']):
                        return 1
        except ValueError:
                return -1
        if float(a['proxim']) == float(b['proxim']):
                return 0
        if float(a['proxim']) < float(b['proxim']):
                return -1
   
def sortByClck(a,b):    # Most recent updates to the top of the list
        if a['clck'] > b['clck']:
                return -1
        if a['clck'] == b['clck']:
                return 0
        if a['clck'] < b['clck']:
                return 1

def secondsPassed(clcktid):
        uret = time.strftime('%H:%M:%S',time.localtime())
        nutid = 3600*int(uret[:2])+60*int(uret[3:5])+int(uret[6:])
        diff = nutid - clcktid
        return diff


        
class AISFlukt(model.Background):
        
        def on_initialize(self, event):                                                  
                self.dataFile = datafile 
                self.myTimer = timer.Timer(self.components.counterField, -1)   # create a timer
                self.myTimer.Start(5000)    # launch timer, to fire every 5000ms (5 seconds)
                self.components.OopsAlert.visible = False
                self.lookAgain()
                self.components.rangeList.insertItems(self.getInRangeList(), 0)
                self.components.sortBy.stringSelection = 'proxim'
                self.showSelected() # This may crash if nada to select from start?
                self.components.splash.visible = True # Flash the splash! It stays True for first loop.

        def on_counterField_timer(self, event):
                selektion = self.selected
                startValue = int(self.components.counterField.text)
                endValue = startValue + 1
                self.components.counterField.text = str(endValue)
                self.lookAgain()
                self.components.rangeList.clear()
                self.components.rangeList.insertItems(self.getInRangeList(), 0)
                self.selected = selektion # This works in an awkward way: The selected \
                                        # item's number is saved and restored across \
                                        # updates, but then often points a new target.\
                                        # How to identify targets persistently?
                self.showSelected()

        def lookAgain(self):
                ''' Opens and reads the census file.
                Builds a new (temporary) dict-list db from this data.'''
                
                retry = 1 
                # Startup sanity test: If the census file doesn't exist yet, \
                # we wait and look again... and again... 
                while retry != 0:
                        try:
                                rows = open(self.dataFile,'r').readlines()
                                retry = 0
                        except IOError:
                                time.sleep(1)
                                retry = 1
                retry = 0
                self.selected = selektion
                self.rowsDict = []
                for r in rows:
                        r = r[:-1]  # Remove the \n here. Duplicated newlines otherwise.
                        r = r.replace(r'\012','\n') # Convert coded 012 back to \n 
                                                        # (dvs octal LF om det finns.)
                        if r.count(',') == 21: # The current number of column(field) \
                                                # separators in the csv file.\
                                                # Critical for this to be accurate.
                                d = {}  # Empty dict
                                i = 0   # Column number incrementor
                                values = r.split(',')
                                for k in columns:
                                        d[k]=values[i].replace(r'\054',',') # Convert octal coded comma to real comma
                                        i+=1
                                self.rowsDict.append(d) # One row --> One dict (cp "Shipfile")
                        else:
                                continue  # IndexErrors may pass uncaught. Won't do?
                        
        def getInRangeList(self):
                ''' Shuffles the target list according to proximity or age'''
                
                l = []
                if self.components.sortBy.stringSelection == 'proxim':
                        self.rowsDict.sort(sortByRange)
                else:
                        self.rowsDict.sort(sortByClck)
        
                for r in self.rowsDict:
                        if self.components.sortBy.stringSelection == 'proxim':
                                l.append( '%s :: %s'%(r['proxim'], r['name']))
                        else:
                                l.append(r['clck'])
                return l

        
        
        def showSelected(self):
                ''' Writes the target's available data fields to the screen'''
                
                if self.selected <0:
                        self.selected = len(self.rowsDict)-1
                if self.selected >= len(self.rowsDict):
                        self.selected = 0 # Should we check for empty rowsDicts here?
                        
                try: # This "try" supresses the intermittent IndexError warnings \
                        # ("list index out of range"), which are probably due to \
                        # random process clashes when accessing census.csv.
                        self.components.mmsi.text = self.rowsDict[self.selected]['mmsi'] 
                        self.components.name.text = self.rowsDict[self.selected]['name']
                        self.components.phono.text = self.rowsDict[self.selected]['phono']
                        self.components.navs.text = self.rowsDict[self.selected]['navs']
                        self.components.vtype.text = self.rowsDict[self.selected]['vtype']
                        self.components.LOA.text = self.rowsDict[self.selected]['LOA']
                        self.components.beam.text = self.rowsDict[self.selected]['beam']
                        self.components.SOG.text = self.rowsDict[self.selected]['SOG']
                        self.components.COG.text = self.rowsDict[self.selected]['COG']
                        self.components.HDG.text = self.rowsDict[self.selected]['HDG']
                        self.components.ROT.text = self.rowsDict[self.selected]['ROT']
                        self.components.LAT.text = self.rowsDict[self.selected]['LAT']
                        self.components.LON.text = self.rowsDict[self.selected]['LON']
                        self.components.proxim.text = self.rowsDict[self.selected]['proxim']
                        self.components.bearing.text = self.rowsDict[self.selected]['bear'] + u'\u00b0'
                        self.components.dest.text = self.rowsDict[self.selected]['dest']
                        self.components.clck.text = self.rowsDict[self.selected]['clck']
                        self.components.secs_since.text = str(secondsPassed(int(self.rowsDict[self.selected]['secs']))) + '"'
                        # Enumeration now starts at 1 not 0 for convenience:
                        self.components.selectedFld.text = str(self.selected + 1)
                        self.components.rangeList._setSelection(int(self.selected))
                        selektion = (int(self.selected))
                        
                        if self.rowsDict[self.selected]['oops'] == 'ok':
                                self.components.OopsAlert.visible = False # Hide the suspect data warning
                        else:
                                self.components.OopsAlert.visible = True # Show ditto
                except IndexError:
                        pass
                self.components.splash.visible = False # Hide the splash screen from now on
       
                ## När man trycker på radioknappar
        def on_sortBy_select(self, event): 
                self.components.sortBy.stringSelection = event.target.stringSelection
                self.components.rangeList.clear()
                self.components.rangeList.insertItems(self.getInRangeList(), 0)

                ## När man väljer i rangelistan: 
        def on_rangeList_select(self, event): 
                self.selected = event.target.selection
                selektion = self.selected
                self.showSelected()

                ## När man väljer siffra med pilknapparna:
        def on_nextButt_mouseDown(self, event):
                self.selected += 1
                self.showSelected()   
        def on_prevButt_mouseDown(self, event):
                self.selected -= 1
                self.showSelected()
                
                ## När man uppdaterar manuellt:
        def on_updateButton_mouseUp(self, event):
                selektion = self.selected
                self.lookAgain()
                self.components.rangeList.clear()
                self.components.rangeList.insertItems(self.getInRangeList(), 0)
                self.selected = selektion
                self.showSelected()

        
if __name__ == '__main__':
        app = model.Application(AISFlukt) # Compulsory PythonCard stuff
        app.MainLoop()
        

