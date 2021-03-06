# -*- coding: utf-8 -*-
#
# Display the "EDSM-Companion" 
#

from collections import defaultdict
import requests
import sys
import threading
import urllib2
import os

import Tkinter as tk
import ttk
from ttkHyperlinkLabel import HyperlinkLabel
import myNotebook as nb

if __debug__:
    from traceback import print_exc

from config import config
from l10n import Locale

VERSION = '0.2'

this = sys.modules[__name__]	# For holding module globals
this.frame = None
this.edsm_session = None
this.edsm_data = None

this.inext = 0
this.edsm_nextsystem = []
this.edsm_testsystem = []
this.iNMSnext = 0
this.edsm_nextNMSsystem = []
this.iNBCnext = 0
this.edsm_nextNBCsystem = []
this.maxbodyId = 0
this.bodies = defaultdict(list)
this.nbodies_null = []
this.nbodies = 0
this.nbodies_dscan = 0
this.nbodies_edsm = []
this.isMainStar = False
this.lock = True
this.lock_systemName = None

this.edsm_nosystem = []
this.edsm_nosystem.append('Andbephi')
this.edsm_nosystem.append('CM Draconis')
this.edsm_nosystem.append('NLTT 18977')
this.edsm_nosystem.append('LP 123-75')
this.edsm_nosystem.append('LP 366-45')
this.edsm_nosystem.append('MCC 515')
this.edsm_nosystem.append('Ross 620')

this.edsm_notexist = []
this.edsm_notexist.append('Synuefai BB-L d9-24')
this.edsm_notexist.append('Synuefai NN-S e4-49')
this.edsm_notexist.append('Synuefai HC-J d10-25')
this.edsm_notexist.append('Synuefai AB-L d9-32')
this.edsm_notexist.append('Wregoe YC-L b49-3')
this.edsm_notexist.append('Wregoe BY-K b49-4')
this.edsm_notexist.append('Wregoe BY-K b49-6')
this.edsm_notexist.append('Wregoe BY-K b49-8')
this.edsm_notexist.append('Wregoe BY-K b49-10')
this.edsm_notexist.append('Wregoe DJ-J b50-1')
this.edsm_notexist.append('Wregoe YI-G c24-13')
this.edsm_notexist.append('Wregoe YI-G c24-18')
this.edsm_notexist.append('Wregoe YI-G c24-21')
this.edsm_notexist.append('Wregoe CP-E c25-17')
this.edsm_notexist.append('Wregoe CP-E c25-18')
this.edsm_notexist.append('Wregoe AC-D d12-9')
this.edsm_notexist.append('Wregoe AC-D d12-62')
this.edsm_notexist.append('Wregoe YG-D d12-33')
this.edsm_notexist.append('Wregoe YG-D d12-52')
this.edsm_notexist.append('Wregoe YG-D d12-56')







def plugin_start():
    # App isn't initialised at this point so can't do anything interesting
    return 'EDSM-Companion'

def plugin_app(parent):
    # Create and display widgets
    this.frame = tk.Frame(parent)
    this.frame.columnconfigure(3, weight=1)
    this.frame.bind('<<EDSMData>>', edsm_data)	# callback when EDSM data received
    this.frame.bind('<<NextData>>', next_data)	# callback when EDSM data received
    this.frame.bind('<<NextNMSData>>', next_NMSdata)	# callback when EDSM data received
    this.frame.bind('<<NextNBCData>>', next_NBCdata)	# callback when EDSM data received
    this.edsm_label = tk.Label(this.frame, text = 'Body Scanned:')
    this.edsm = tk.Label(this.frame)
    this.edsmnext_label = tk.Label(this.frame, text = 'Next NoEDSM: [0]')
    this.edsmnext = HyperlinkLabel(this.frame)
    this.edsmnext.bind("<Button-1>", copy_to_clipboard)
    this.edsmNMSnext_label = tk.Label(this.frame, text = 'Next NoMainStar: [0]')
    this.edsmNMSnext = HyperlinkLabel(this.frame)
    this.edsmNMSnext.bind("<Button-1>", NMScopy_to_clipboard)
    this.edsmNBCnext_label = tk.Label(this.frame, text = 'Next NoBodyCount: [0]')
    this.edsmNBCnext = HyperlinkLabel(this.frame)
    this.edsmNBCnext.bind("<Button-1>", NBCcopy_to_clipboard)
    this.spacer = tk.Frame(this.frame)	# Main frame can't be empty or it doesn't resize
    this.button = ttk.Button(frame, text='Status = Locked', width=28, default=tk.ACTIVE)
    this.button.bind("<Button-1>", Switch_Lock)
    update_visibility()
    return this.frame

def plugin_prefs(parent, cmdr, is_beta):
    frame = nb.Frame(parent)

    nb.Label(frame, text = 'Version %s' % VERSION).grid(padx = 10, pady = 10, sticky=tk.W)

    return frame

def prefs_changed(cmdr, is_beta):
    update_visibility()


def journal_entry(cmdr, is_beta, system, station, entry, state):

    if entry['event'] == 'FSSDiscoveryScan':
        this.nbodies_dscan = entry['BodyCount']
        this.edsm['text'] = str(len(this.nbodies_edsm))+("*" if this.isMainStar else "")+' / '+str(this.nbodies)+' / '+str(this.nbodies_dscan)
    
    if entry['event'] == 'Scan':
        if not entry['BodyName'] in this.nbodies_edsm:
            this.nbodies_edsm.append(entry['BodyName'])
            if entry['BodyID'] > this.maxbodyId:
                this.maxbodyId = entry['BodyID']
            if 'StarType' in entry:
                if entry['DistanceFromArrivalLS']==0.0:
                    this.isMainStar = True
            if 'Parents' in entry:
                k = 0
                for parent in entry['Parents']:
                    #if 'Ring' in parent:
                    #    if not entry['BodyID'] in this.nbodies_null:
                    #        this.nbodies_null.append(entry['BodyID'])
                    if 'Null' in parent:
                        if not parent['Null'] in this.nbodies_null:
                            this.nbodies_null.append(parent['Null'])
                    k += 1
            this.nbodies = this.maxbodyId + 1 - len(this.nbodies_null)
            this.edsm['text'] = str(len(this.nbodies_edsm))+("*" if this.isMainStar else "")+' / '+str(this.nbodies)+' / '+str(this.nbodies_dscan)
            

    #print(entry)
    #print(entry['event'] == 'FSDJump', entry['event'] in ['Location', 'FSDJump'])
    if entry['event'] in ['Location', 'FSDJump', 'StartUp']:
        if not this.lock:
            this.inext = 0
            this.edsm_nextsystem = []
            this.edsm_testsystem = []
            this.iNMSnext = 0
            this.edsm_nextNMSsystem = []
            this.iNBCnext = 0
            this.edsm_nextNBCsystem = []
            this.lock_systemName = entry['StarSystem']
            
        this.maxbodyId = 0
        this.bodies = defaultdict(list)
        this.nbodies_null = []
        this.nbodies = 0
        this.nbodies_dscan = 0
        this.nbodies_edsm = []
        this.systemName = entry['StarSystem']
        this.isMainStar = False
    
        thread = threading.Thread(target = edsm_worker, name = 'EDSM worker', args = (this.systemName,int(entry['SystemAddress']),))
        thread.daemon = True
        thread.start()


#def cmdr_data(data, is_beta):
    # Manual Update
#    thread = threading.Thread(target = edsm_worker, name = 'EDSM worker', args = (data['lastSystem']['name'],None))
#    thread.daemon = True
#    thread.start()

# EDSM lookup
def edsm_worker(systemName, id64_dec):

    if not this.edsm_session:
        this.edsm_session = requests.Session()

    try:
        r = this.edsm_session.get('https://www.edsm.net/api-system-v1/bodies?systemName=%s' % urllib2.quote(systemName), timeout=20)
        r.raise_for_status()
        this.edsm_data = r.json()
    except:
        this.edsm_data = None

    this.frame.event_generate('<<EDSMData>>', when='tail')

    if this.lock:
        return

    #bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode = id64_splitbin("{0:064b}".format(1831560284547))
    #print('test=',bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode)
    #bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode = id64_splitbin("{0:064b}".format(3858784848259))
    #print('test=',bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode)
    #bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode = id64_splitbin("{0:064b}".format(36030628579248510))
    #print('test=',bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode)
    #bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode = id64_splitbin("{0:064b}".format(72059425598212480))
    #print('test=',bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode)
    
    if id64_dec is not None:
        id64 = "{0:064b}".format(id64_dec)
        bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode = id64_splitbin(id64)
        MCode = int(bit_MCode, 2)
        namesector,posID,n2 = id64toName(bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode)

        #print(namesector,posID,n2)
        
        for i in range(200):
            newn2 = ("{0:0%sb}" % len(str(bit_n2))).format(i)
            if(n2==i):
                #print(namesector+" "+posID+"-"+str(i))
                this.edsm_testsystem.append(namesector+" "+posID+"-"+str(i))
                continue
            if namesector+" "+posID+"-"+str(i) in this.edsm_notexist:
                continue
            #print(namesector,posID,i)
            newid64 = str(bodyId)+str(newn2)+str(xsector)+str(xcoord)+str(ysector)+str(ycoord)+str(zsector)+str(zcoord)+str(bit_MCode)
            newid64 = int(newid64, 2)
            r_test = this.edsm_session.get('https://www.edsm.net/api-v1/system?systemId64=%s&showId=1' % newid64, timeout=20)
            r_test.raise_for_status()
            edsm_test = r_test.json()
            #if 'name' in edsm_system:
            #print(i, "   ", namesector+" "+posID+"-"+str(i))
            #else:
            if not 'name' in edsm_test:
                #print(i, "UNK", namesector+" "+posID+"-"+str(i))
                #print(namesector+" "+posID+"-"+str(i))
                this.edsm_testsystem.append(namesector+" "+posID+"-"+str(i))
                this.edsm_nextsystem.append(namesector+" "+posID+"-"+str(i))
                print('NoEDSM : %s - %s - %s' % (len(this.edsm_nextsystem),newid64, namesector+" "+posID+"-"+str(i)))
                break
            
        this.frame.event_generate('<<NextData>>', when='tail')
        #print(this.edsm_nextsystem)

        minradius = 0
        stepradius = 10
        radius = 20
        findradius = False
        findNMSradius = False
        findNBCradius = False
        
        for rmax in range(4):
            #print("radius=",radius)
            r_sphere = this.edsm_session.get('https://www.edsm.net/api-v1/sphere-systems?systemName=%s&minRadius=%s&radius=%s&showId=1&showPrimaryStar=1' % (urllib2.quote(systemName),urllib2.quote(str(minradius)),urllib2.quote(str(radius))), timeout=40)
            r_sphere.raise_for_status()
            edsm_sphere = r_sphere.json()
            minradius = radius
            radius += stepradius

            if not findNBCradius:
                for edsm_system in edsm_sphere:
                    #print('bodyCount = ',edsm_system['bodyCount'])
                    if(edsm_system['bodyCount'] is None and edsm_system['distance']!=0 and edsm_system['name']!=systemName):
                        if not edsm_system['name'] in this.edsm_nextNBCsystem:
                            if not edsm_system['name'] in this.edsm_nosystem:
                                findNBCradius = True
                                this.edsm_nextNBCsystem.append(edsm_system['name'])
                                #print("EDSM :",edsm_system['name'])
                                print('NoBodyCount : %s - %s' % (len(this.edsm_nextNBCsystem), edsm_system['name']))
                                this.frame.event_generate('<<NextNBCData>>', when='tail')
                                
            if not findNMSradius:
                for edsm_system in edsm_sphere:
                    if(edsm_system['primaryStar'] is None and edsm_system['distance']!=0 and edsm_system['name']!=systemName):
                        if not edsm_system['name'] in this.edsm_nextNMSsystem:
                            if not edsm_system['name'] in this.edsm_nosystem:
                                findNMSradius = True
                                this.edsm_nextNMSsystem.append(edsm_system['name'])
                                #print("EDSM :",edsm_system['name'])
                                print('NoMainStar : %s - %s' % (len(this.edsm_nextNMSsystem), edsm_system['name']))
                                this.frame.event_generate('<<NextNMSData>>', when='tail')

            if not findradius:
                for k in range(8):
                    #print("k=",k)
                    
                    find = False
                    for edsm_system in edsm_sphere:

                        id64 = "{0:064b}".format(edsm_system['id64'])
                        bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode = id64_splitbin(id64)
                        MCode = int(bit_MCode, 2)
                        
                        #print(MCode,edsm_system['name'])
                        
                        if k==MCode:
                            namesector,posID,n2 = id64toName(bodyId,bit_n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode)

                            #if(not namesector+" "+posID in this.edsm_testsystem):
                            #    this.edsm_testsystem.append(namesector+" "+posID)
                            #else:
                            #    continue
                            #print(MCode)
                            #print(namesector,posID,n2)
                            
                            for i in range(0,n2):
                                if namesector+" "+posID+"-"+str(i) in this.edsm_notexist:
                                    continue
                                if(not namesector+" "+posID+"-"+str(i) in this.edsm_testsystem):
                                    this.edsm_testsystem.append(namesector+" "+posID+"-"+str(i))
                                else:
                                    continue
                                newn2 = ("{0:0%sb}" % len(str(bit_n2))).format(i)
                                #print(namesector,posID,n2-i)
                                newid64 = str(bodyId)+str(newn2)+str(xsector)+str(xcoord)+str(ysector)+str(ycoord)+str(zsector)+str(zcoord)+str(bit_MCode)
                                newid64 = int(newid64, 2)
                                r_test = this.edsm_session.get('https://www.edsm.net/api-v1/system?systemId64=%s&showId=1' % newid64, timeout=10)
                                r_test.raise_for_status()
                                edsm_test = r_test.json()

                                #print(namesector+" "+posID+"-"+str(n2-i))
                                #print(edsm_test)
                                if not 'name' in edsm_test:
                                    #print(i, "UNK", namesector+" "+posID+"-"+str(i))
                                    if not namesector+" "+posID+"-"+str(i) in this.edsm_nextsystem:
                                        find = True
                                        findradius = True
                                        this.edsm_nextsystem.append(namesector+" "+posID+"-"+str(i))
                                        print('NoEDSM : %s - %s - %s' % (len(this.edsm_nextsystem),newid64, namesector+" "+posID+"-"+str(i)))
                                        this.frame.event_generate('<<NextData>>', when='tail')
                                        #break
                                
                            #if find:
                            #    break
            if findradius and findNMSradius and findNBCradius:
                break
        #print(this.edsm_nextsystem)

        # Tk is not thread-safe, so can't access widgets in this thread.
        # event_generate() is the only safe way to poke the main thread from this thread.
        #this.frame.event_generate('<<NextData>>', when='tail')


# EDSM data received
def edsm_data(event):

    if this.edsm_data is None:
        # error
        this.edsm['text'] = '?'+' / '+'?'+' / '+str(this.nbodies_dscan)
        return

    # Collate
    this.nbodies_edsm = []
    for body in this.edsm_data.get('bodies', []):
        this.nbodies_edsm.append(body['name'])
        if 'isMainStar' in body:
            if body['isMainStar']:
                this.isMainStar = True
        
        if body['bodyId'] > this.maxbodyId:
            this.maxbodyId = body['bodyId']
        
        if 'parents' in body:
            if body['parents'] is not None:
                k = 0
                for parent in body['parents']:
                    if 'Null' in parent:
                        if not parent['Null'] in this.nbodies_null:
                            this.nbodies_null.append(parent['Null'])
                    k += 1
        this.nbodies = this.maxbodyId + 1 - len(this.nbodies_null)

    this.edsm['text'] = str(len(this.nbodies_edsm))+("*" if this.isMainStar else "")+' / '+str(this.nbodies)+' / '+str(this.nbodies_dscan)

def next_data(event):
    #print(this.edsm_nextsystem)
    this.edsmnext_label['text'] = 'Next NoEDSM: ['+str(this.inext+1)+'/'+str(len(this.edsm_nextsystem))+']'
    this.edsmnext['text'] = this.edsm_nextsystem[this.inext]
    this.edsmnext['url'] = this.edsm_nextsystem[this.inext]

def next_NMSdata(event):
    #print(this.edsm_nextsystem)
    this.edsmNMSnext_label['text'] = 'Next NoMainStar: ['+str(this.iNMSnext+1)+'/'+str(len(this.edsm_nextNMSsystem))+']'
    this.edsmNMSnext['text'] = this.edsm_nextNMSsystem[this.iNMSnext]
    this.edsmNMSnext['url'] = this.edsm_nextNMSsystem[this.iNMSnext]

def next_NBCdata(event):
    #print(this.edsm_nextsystem)
    this.edsmNBCnext_label['text'] = 'Next NoBodyCount: ['+str(this.iNBCnext+1)+'/'+str(len(this.edsm_nextNBCsystem))+']'
    this.edsmNBCnext['text'] = this.edsm_nextNBCsystem[this.iNBCnext]
    this.edsmNBCnext['url'] = this.edsm_nextNBCsystem[this.iNBCnext]

def update_visibility():
    row = 1
    this.edsm_label.grid(row = row, column = 0, sticky=tk.W)
    this.edsm.grid(row = row, column = 1, columnspan=5, sticky=tk.W)
    row += 1
    this.edsmNMSnext_label.grid(row = row, column = 0, sticky=tk.W)
    this.edsmNMSnext.grid(row = row, column = 1, columnspan=5, sticky=tk.W)
    row += 1
    this.edsmNBCnext_label.grid(row = row, column = 0, sticky=tk.W)
    this.edsmNBCnext.grid(row = row, column = 1, columnspan=5, sticky=tk.W)
    row += 1
    this.edsmnext_label.grid(row = row, column = 0, sticky=tk.W)
    this.edsmnext.grid(row = row, column = 1, columnspan=5, sticky=tk.W)
    row += 1
    this.button.grid(row = row, columnspan=6, sticky=tk.NSEW)
    this.spacer.grid(row = 0)

def copy_to_clipboard(event):
    window=tk.Tk()
    window.withdraw()
    window.clipboard_clear()  # clear clipboard contents
    window.clipboard_append(this.edsm_nextsystem[this.inext])
    window.destroy()

    this.inext += 1
    if this.inext >= len(this.edsm_nextsystem):
        this.inext=0
    this.edsmnext_label['text'] = 'Next NoEDSM: ['+str(this.inext+1)+'/'+str(len(this.edsm_nextsystem))+']'
    this.edsmnext['text'] = this.edsm_nextsystem[this.inext]
    this.edsmnext['url'] = this.edsm_nextsystem[this.inext]

def NMScopy_to_clipboard(event):
    window=tk.Tk()
    window.withdraw()
    window.clipboard_clear()  # clear clipboard contents
    window.clipboard_append(this.edsm_nextNMSsystem[this.iNMSnext])
    window.destroy()

    this.iNMSnext += 1
    if this.iNMSnext >= len(this.edsm_nextNMSsystem):
        this.iNMSnext=0
    this.edsmNMSnext_label['text'] = 'Next NoMainStar: ['+str(this.iNMSnext+1)+'/'+str(len(this.edsm_nextNMSsystem))+']'
    this.edsmNMSnext['text'] = this.edsm_nextNMSsystem[this.iNMSnext]
    this.edsmNMSnext['url'] = this.edsm_nextNMSsystem[this.iNMSnext]

def NBCcopy_to_clipboard(event):
    window=tk.Tk()
    window.withdraw()
    window.clipboard_clear()  # clear clipboard contents
    window.clipboard_append(this.edsm_nextNBCsystem[this.iNBCnext])
    window.destroy()

    this.iNBCnext += 1
    if this.iNBCnext >= len(this.edsm_nextNBCsystem):
        this.iNBCnext=0
    this.edsmNBCnext_label['text'] = 'Next NoBodyCount: ['+str(this.iNBCnext+1)+'/'+str(len(this.edsm_nextNBCsystem))+']'
    this.edsmNBCnext['text'] = this.edsm_nextNBCsystem[this.iNBCnext]
    this.edsmNBCnext['url'] = this.edsm_nextNBCsystem[this.iNBCnext]

def Switch_Lock(event):
    if this.lock:
        this.lock = False
        this.button['text'] = 'Status = Unlocked'
    else:
        this.lock = True
        if this.lock_systemName is None:
            this.button['text'] = 'Status = Locked'
        else:
            this.button['text'] = 'Status = Locked '+'('+str(this.lock_systemName)+')'
    
def id64_splitbin(id64):

    bit_MCode = id64[len(id64)-3:]
    MCode = int(bit_MCode, 2)
    nbit_boxel = 7-MCode
    #print(MCode,nbit_boxel)
    tmpid64 = id64[:len(id64)-3]
    zcoord = tmpid64[len(tmpid64)-nbit_boxel:]
    #print(zcoord)
    tmpid64 = tmpid64[:len(tmpid64)-nbit_boxel]
    zsector = tmpid64[len(tmpid64)-7:]
    #print(zsector)
    tmpid64 = tmpid64[:len(tmpid64)-7]
    ycoord = tmpid64[len(tmpid64)-nbit_boxel:]
    #print(ycoord)
    tmpid64 = tmpid64[:len(tmpid64)-nbit_boxel]
    ysector = tmpid64[len(tmpid64)-6:]
    #print(ysector)
    tmpid64 = tmpid64[:len(tmpid64)-6]
    xcoord = tmpid64[len(tmpid64)-nbit_boxel:]
    #print(xcoord)
    tmpid64 = tmpid64[:len(tmpid64)-nbit_boxel]
    xsector = tmpid64[len(tmpid64)-7:]
    #print(xsector)
    tmpid64 = tmpid64[:len(tmpid64)-7]
    n2bit = nbit_boxel*3+7+7+6+3
    n2 = tmpid64[9:]
    #print(n2)
    bodyId = tmpid64[:9]
    #print(bodyId)

    return bodyId,n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode
    

def id64toName(bodyId,n2,xsector,xcoord,ysector,ycoord,zsector,zcoord,bit_MCode):

    MCode = int(bit_MCode, 2)
    
    fb=open(os.path.dirname(this.__file__)+'\\'+'sectors.txt', 'r')
    for lineb in fb:
        jline = lineb[:-1].split(",")
        x = "{0:07b}".format(int((49985.0 + float(jline[0]))/1280))
        y = "{0:06b}".format(int((40985.0 + float(jline[1]))/1280))
        z = "{0:07b}".format(int((24105.0 + float(jline[2]))/1280))
        if x==xsector and y==ysector and z==zsector:
            namesector = jline[3]
            break
    fb.close()

    boxID = int(xcoord, 2)+int(ycoord, 2)*128+int(zcoord, 2)*128*128
    l1 = boxID % 26
    r1 = boxID - l1
    l2 = int(r1/26) % 26
    r2 = int(r1/26) - l2
    l3 = int(r2/26) % 26
    r3 = int(r2/26) - l3
    n1 = int(r3/26)
    n2_dec = int(n2, 2)

    posID = chr(ord('A')+l1)+chr(ord('A')+l2)+"-"+chr(ord('A')+l3)+" "+chr(ord('a')+MCode)+str(n1)

    return namesector,posID,n2_dec
