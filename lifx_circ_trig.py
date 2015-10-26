# -*- coding: utf-8 -*-
"""
Created on Fri Oct 16 08:36:28 2015

@author: handsheik

TO DO:
• HTTP SERVER / SWITCH
• LOAD STATES / TOKEN / LAT / LONG FROM JSON FILE
• AUTO - FIRE NEXT CUE
• SUNRISE / SET RESET AT MIDNIGHT?
"""

from datetime import datetime
import json
from math import floor
from pprint import pprint
import requests
import time
import multiprocessing
import subprocess

import ephem
import lifx_api_creds
#import tornado.websocket
#import tornado.httpserver
#import tornado.ioloop

VERBOSE = 1
LIFX_URL = "https://api.lifx.com/v1/"
STATE_URL = "https://api.lifx.com/v1/lights/all/state"
SWITCH_OFF_FADEOUT = 3.0
SWITCH_ON_FADEIN = 1.0

lights_on = True

class LightState():
    def __init__(self, name, bright, start, 
                 hue = None, sat = None, kelvin = None):
        self.name = name
        self.bright = bright
        self.start = start
        self.hue = hue          
        self.sat = sat
        self.kelvin = kelvin
        if hue is None:
            self.type = "white"
        else:
            self.type = "color"
        
    def __repr__(self):
        rep = "///LS NAME: {}, ".format(self.name)
        rep += "bright: {}, ".format(self.bright)
        rep += "start: {}, ".format(self.start)
        rep += "hue: {}, ".format(self.hue)
        rep += "sat: {}, ".format(self.sat)
        rep += "kelvin: {} ".format(self.kelvin)
        return  rep
        
    def is_color(self):
        return self.type is "color"
    
    def is_white(self):
        return self.type is "white"

#class IndexHandler(tornado.web.RequestHandler):
#    """HTTP request handler to serve HTML for switch server"""
#    def get(self):
#        self.render('index.html')
#
#class SwitchWSHandler(tornado.websocket.WebSocketHandler):
#    """Receives switch commands from the switch web view"""
#    def open(self):
#        print 'new connection'
#        self.write_message('yo homie light server here')
#
#    def on_message(self, message):
#        print 'SWITCH message received:  %s' % message
#        self.write_message('got your query thanks homie')
#        if message == 'ON':
#            switch_on()
#        elif message == 'OFF':
#            switch_off()
#        else:
#            print('UNUSABLE MESSAGE FROM SWITCH')
#
#    def on_close(self):
#        print 'connection closed'
#
#    def check_origin(self, origin):
#        return True

def test_connection():
    response = requests.get('https://api.lifx.com/v1/lights/all',
                            headers=lifx_api_creds.headers)
    response_json = json.loads(response.text)
    print 'TESTING.......'
#    if VERBOSE:
#        print response_json
    print '-----------------'
    light_num = 0
    for r in response_json:
        print('-------- LIGHT NUM: ' + str(light_num) + ' ---------')
        print('-------- NAME: ' + str(r[u'label']) + ' --------')
        print('-------- COLOR: ' + str(r[u'color']) + ' ---------')
        print('-------- BRIGHT: ' + str(r[u'brightness']) + ' ---------')
        #print r
        print('-------- POWER:  ' + r[u'power'] + ' ---------')
        print('///////////')
        light_num += 1
    print(response_json[1][u'power'])
    if response_json[0][u'power'] == 'on':
        print('THE LIGHTS ARE ON')
    else:
        print('THE LIGHTS ARE OFF')

def day_frac_to_secs(day_frac):
    """ accepts TOD as fraction and returns seconds """
    return float(day_frac) * 86400

def secs_to_day_frac(secs):
    """ accepts seconds and returns TOD as fraction """
    if secs:
        return float(secs) / 86400
    else:
        return 0

def secs_to_hr_min_sec(secs):
    """ accepts seconds and returns (h,m,s) tuple """
    if secs:
        hrs = int(floor(secs / 60 / 60))
        mins = int(floor(secs / 60 % 60))
        secs = int(floor(secs % 60))
        return (hrs, mins, secs)
    else:
        return (0,0,0)

def secs_into_day():
    """ returns the number of seconds since midnight """
    now = datetime.now().time()
    return ((now.hour * 60 * 60) + (now.minute * 60) + now.second)


def print_time_from_day_frac(day_frac):
    """ accepts TOD as fraction and prints and returns time string as h:m:s """
    secs = day_frac_to_secs(day_frac)
    c_hr,c_min,c_sec = secs_to_hr_min_sec(secs)
    str_to_print = '{}:{}:{}'.format(c_hr,c_min,c_sec)
    print str_to_print
    return str_to_print

def switch_on_from(lut):
    global lights_on
    lights_on = True
    
    cur_time = secs_to_day_frac(secs_into_day())
    if VERBOSE:
        print 'cur_time frac: ', cur_time
        print_time_from_day_frac(cur_time)

    # refactor using enumerate:
    # for i, st in enumerate(lut): 
    for i in range(0,len(lut)-1):
        st = lut[i]
        next_start = st.start
        if next_start > cur_time:
            
            if i is 0:
                prev_index = len(lut) - 1
            else:
                prev_index = i - 1     
                
            pv_st = lut[prev_index]    
            
            if VERBOSE:
                print('currently in state: '+str(pv_st.name))
                print('current state start time: ' + str(pv_st.start))
                print('next state start time: ' + str(next_start))

            # calculate how far we are into the current state
            time_in = cur_time - pv_st.start
            if VERBOSE:
                print('abs time in to this state: ' + str(time_in))
            
            # calculate what percentage we are into the current state
            frac_in  = time_in / (next_start - pv_st.start)
            if VERBOSE:
                print ('frac in: ' + str(frac_in))
        
            # calculate interpolated hue
            prev_hue = pv_st.hue
            next_hue = st.hue
            cur_hue = frac_in * (next_hue - prev_hue) + prev_hue
            if VERBOSE:
                print 'cur_hue: ', cur_hue            
            
            # calculate interpolated saturation
            prev_sat = pv_st.sat
            next_sat = st.sat
            cur_sat = frac_in * (next_sat - prev_sat) + prev_sat
            if VERBOSE:
                print 'cur_sat: ', cur_sat            
            
            # calculate interpolated brightness
            prev_bright = pv_st.bright
            next_bright = st.bright
            cur_bright = frac_in * (next_bright - prev_bright) + prev_bright
            if VERBOSE:
                print 'cur_bright: ', cur_bright
                
            # calculate interpolated kelvin
            prev_kelvin = pv_st.kelvin
            next_kelvin = st.kelvin
            cur_kelvin = int(frac_in * 
                               (next_kelvin - prev_kelvin) + prev_kelvin)
            if VERBOSE:
                print 'cur_kelvin: ', cur_kelvin

            # calculate remaining duration in current state
            dur = next_start - cur_time
            dur_secs = day_frac_to_secs(dur)
            if VERBOSE:
                print('dur secs remaining: ' + str(dur_secs))
                
            # switch on at current pro-rated settings over 1s
            if cur_sat:
                set_all_to_hsb(cur_hue, cur_sat, cur_bright, SWITCH_ON_FADEIN)
            else:
                set_all_to_hsbk(cur_hue, cur_sat, cur_bright, 
                                cur_kelvin, SWITCH_ON_FADEIN)
            time.sleep(SWITCH_ON_FADEIN)
            if st.sat:
                set_all_to_hsb(st.hue, st.sat, st.bright, dur_secs)
            else:
                set_all_to_hsbk(st.hue, st.sat, st.bright, st.kelvin, dur_secs)
            break

def switch_off():
    global lights_on
    lights_on = False
    c_s = str('brightness:0.0')
    put_request(c_s,SWITCH_OFF_FADEOUT)
    print('switching off')

def put_request(c_s, duration):
    """ take a formatted color string and duration float
    and put that request to the LIFX API """
    if VERBOSE:
        print('put request: {}, {}'.format(c_s,duration))
    data = json.dumps(
        {'selector':'all',
         'power':'on',
         'color':c_s,
         'duration':duration,
         })
    r = requests.put(STATE_URL, data, headers=lifx_api_creds.headers)
    print (r)
    
def set_all_to_hsbk(hue,saturation,brightness,kelvin,duration):
    if not lights_on:
        brightness = 0
    if saturation:
        # we are setting a color - assign Kelvin first 
        c_s = str('kelvin:'+str(kelvin) + 
            ' hue:'+str(hue)+
            ' saturation:'+str(saturation)+
            ' brightness:'+str(brightness))
    else:
        # we are setting a white - assign Kelvin last and
        # the API will set the sat to 0
        c_s = str('hue:'+str(hue)+
            ' saturation:'+str(saturation)+
            ' brightness:'+str(brightness)+
            ' kelvin:'+str(kelvin))
    put_request(c_s,duration)

def load_file():
    with open('data.json') as data_file:    
        return json.load(data_file)
#    pprint(data)

def build_lut(data):
    states = data['states']
    lut = []
    for s in states:
        ls = LightState(s['name'],s['bright'],s['start'],s['hue'],s['sat'],
                            kelvin = s['kelvin'])
        lut.append(ls)
    return lut

#def popenAndCall(onExit, popenArgs):
#    """
#    Runs the given args in a subprocess.Popen, and then calls the function
#    onExit when the subprocess completes.
#    onExit is a callable object, and popenArgs is a list/tuple of args that 
#    would give to subprocess.Popen.
#    """
#    def runInThread(onExit, popenArgs):
#        proc = subprocess.Popen(*popenArgs)
#        proc.wait()
#        onExit()
#        return
#    process = multiprocessing.Process(target=runInThread, args=(onExit, popenArgs))
#    process.start()
#    # returns immediately after the thread starts
#    return process

def onExit():
    print 'IM BACK MUTHAFUCK: '


test_connection()
data = load_file()
print 'HEADERS: ', lifx_api_creds.headers
lut = build_lut(data)
print 'LUT: ', lut
switch_on_from(lut)
#switch_off()


o=ephem.Observer()
o.lat='40.677365'
o.long='-73.963063'
sun=ephem.Sun()
sun.compute()

next_rise = ephem.localtime(o.next_rising(sun))
next_set = ephem.localtime(o.next_setting(sun))

today_length = next_rise - next_set

#print( next_rise.timetuple().tm_hour )

