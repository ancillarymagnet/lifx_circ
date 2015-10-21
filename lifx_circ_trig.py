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
from collections import OrderedDict
from math import floor
import json
import time
from pprint import pprint

import ephem
import requests
#import tornado.websocket
#import tornado.httpserver
#import tornado.ioloop

VERBOSE = 1
TOKEN = "ceba30aa6fb710396f536a496b06b94a00f2eeec29065f53edb8da896dc4234e"
LIFX_URL = "https://api.lifx.com/v1/"
STATE_URL = "https://api.lifx.com/v1/lights/all/state"
HEADERS = {
    "Authorization": "Bearer %s" % TOKEN,
}
SWITCH_OFF_FADEOUT = 3.0
OVERNIGHT = 0.0
SUNRISE = 0.3125 # override with ephem
MIDMORN = 0.41666 # 10am
MIDDAY = 0.541666 # 1pm
SUNSET = 0.8125 # override with ephem
BED = 0.9375
TIMES = [OVERNIGHT, SUNRISE, MIDMORN, MIDDAY, SUNSET, BED]
STATES = OrderedDict()

lights_on = False

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
        rep = "LightState name: {}, ".format(self.name)
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

def init_states():
    # for each entry in JSON add to ordered dictionary
    STATES['overnight'] = {'start':OVERNIGHT, 'hue':0, 'sat':1.0, 'bright':0.02}
    STATES['sunrise'] = {'start':SUNRISE, 'hue':30, 'sat':1.0, 'bright':0.65}
    STATES['mid-morn'] = {'start':MIDMORN, 'kelvin':4000, 'bright':0.8}
    STATES['mid-day'] = {'start':MIDDAY, 'kelvin':5500, 'bright':1.0}
    STATES['dinner'] = {'start':SUNSET, 'hue':50, 'sat':1.0, 'bright':0.55}
    STATES['bed'] = {'start':BED, 'hue':20, 'sat':1.0, 'bright':0.05}

def test_connection():
    response = requests.get('https://api.lifx.com/v1/lights/all',
                            headers=HEADERS)
    response_json = json.loads(response.text)
    print 'TESTING.......'
    if VERBOSE:
        print response_json
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

def switch_on():
    # figure out where we are, fractionally, in the day
    # figure out where we are, fractionally, between keys
    # 'jump' into that key with the pro-rated brightness xition to the next
    global lights_on
    lights_on = True
    cur_time = secs_to_day_frac(secs_into_day())
    if VERBOSE:
        print 'cur_time frac: ', cur_time
        print_time_from_day_frac(cur_time)
    prev_start = 0.0
    prev_key = 'none'

    for st in STATES.items():
        k,v = st
        next_start = v['start']
#        if VERBOSE:
#            print 'next_start pre-comparison: ' + str(next_start)
#            print 'prev_start pre-comparison: ' + str(prev_start)

        if next_start > cur_time:
            if VERBOSE:
                print('currently in state: '+str(prev_key))
                print('current state start time: ' + str(prev_start))
                print('next state start time: ' + str(next_start))

            # calculate how far we are into the current state
            time_in = cur_time - prev_start
            if VERBOSE:
                print('abs time in to this state: ' + str(time_in))

            # calculate what percentage we are into the current state
            frac_in  = time_in / (next_start - prev_start)
            if VERBOSE:
                print ('frac in: ' + str(frac_in))

            # calculate pro-rated brightness for current state
            prev_bright = STATES[prev_key]['bright']
            next_bright = v['bright']
            cur_bright = frac_in * (next_bright - prev_bright) + prev_bright
            if VERBOSE:
                print 'cur_bright: ', cur_bright

            # calculate remaining duration in current state
            dur = next_start - cur_time
            dur_secs = day_frac_to_secs(dur)
            if VERBOSE:
                print('dur secs remaining: ' + str(dur_secs))
                
            # this is making the assumption that the previous state's
            # color / k is already set
            set_all_to_bright(cur_bright,1.0)
            time.sleep(1.0)
            # check if next state is a color or kelvin and transish
            if v.has_key('hue'):
                h = v['hue']
                s = v['sat']
                set_all_to_color(h,s,next_bright,dur_secs)
                if VERBOSE:
                    print 'setting next state {}: h:{} s:{} b:{} d:{}'.format(
                        k,h,s,next_bright,dur_secs)
            else:
                kel = v['kelvin']
                set_all_to_kelvin(kel,next_bright,dur_secs)
                if VERBOSE:
                    print 'setting next state {}: k:{} b:{} d:{}'.format(
                        k,kel,next_bright,dur_secs)
            break
        else:
            prev_start = next_start
            prev_key = k
    # go_to_state(state,duration)

def switch_off():
    global lights_on
    lights_on = False
    c_s = str('brightness:0.0')
    put_request(c_s,SWITCH_OFF_FADEOUT)
    print('switching off')

def put_request(c_s, duration):
    if VERBOSE:
        print('put request: {}, {}'.format(c_s,duration))
    data = json.dumps(
        {'selector':'all',
         'power':'on',
         'color':c_s,
         'duration':duration,
         })
    r = requests.put(STATE_URL, data, headers=HEADERS)
    print (r)

def go_to_state(s,duration):
    if not STATES.has_key(s):
        print('invalid state: ' + str(s))
    else:
        state = STATES[s]
        b = state['bright']
        if state.has_key('kelvin'):
            k = state['kelvin']
            set_all_to_kelvin(k,b,duration)
        else:
            h = state['hue']
            s = state['sat']
            set_all_to_color(h,s,b,duration)

def set_all_to_kelvin(kelvin,brightness,duration):
    if not lights_on:
        brightness = 0
    c_s = str('kelvin:'+str(kelvin)+
        ' brightness:'+str(brightness))
    put_request(c_s,duration)

def set_all_to_color(hue,saturation,brightness,duration):
    if not lights_on:
        brightness = 0
    c_s = str('hue:'+str(hue)+
            ' saturation:'+str(saturation)+
            ' brightness:'+str(brightness))
    put_request(c_s,duration)

def set_all_to_bright(brightness,duration):
    if not lights_on:
        brightness = 0
    c_s = str('brightness:'+str(brightness))
    if VERBOSE:
        print 'switching all to bright: {} dur: {}'.format(brightness, duration)
    put_request(c_s,duration)

def load_file():
    with open('data.json') as data_file:    
        data = json.load(data_file)
        
    pprint(data)
    print 'token: ' + data['token']


init_states()
test_connection()
set_all_to_color(20,1.0,0.74,1.0)
switch_on()
load_file()
test_state = LightState("test",1.0,0.57,kelvin=5000)
print test_state
print test_state.is_white()
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


#test_connection()
#set_all_to_color(240,1.0,1.0,5.0)
#time.sleep(5)
#set_all_to_kelvin(2500,1.0,1.0)
#test_connection()






"""
{
  "selector": "all",
  "power": "on",
  "color": "blue saturation:0.5",
  "brightness": 0.5,
  "duration": 5
}
"""