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

#from datetime import datetime, date, time
import datetime
import json
from math import floor
from pprint import pprint
import pytz
import requests
import time
import multiprocessing
import subprocess

import ephem
import lifx_api_creds
#import tornado.websocket
#import tornado.httpserver
#import tornado.ioloop

lights_on = True

class LightState():
    def __init__(self, name, bright, start,
                 hue=None, sat=None, kelvin=None):
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

def cond_print(print_string):
    if VERBOSE:
        print print_string

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
    cond_print(response_json[1][u'power'])

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
        return (0, 0, 0)

def secs_into_day():
    """ returns the number of seconds since midnight """
    now = datetime.datetime.now().time()
    return ((now.hour * 60 * 60) + (now.minute * 60) + now.second)

def print_time_from_day_frac(day_frac):
    """ accepts TOD as fraction and prints and returns time string as h:m:s """
    secs = day_frac_to_secs(day_frac)
    c_hr, c_min, c_sec = secs_to_hr_min_sec(secs)
    str_to_print = '{}:{}:{}'.format(c_hr, c_min, c_sec)
    print str_to_print
    return str_to_print

def datetime_to_day_frac(dt):
    hrs = dt.time().hour
    mins = dt.time().minute
    secs = dt.time().second
    return secs_to_day_frac((hrs * 60 * 60) + (mins * 60) + secs)

def switch_on_from(lut):
    global lights_on
    lights_on = True

    cur_time = secs_to_day_frac(secs_into_day())
    if VERBOSE:
        print_time_from_day_frac(cur_time)

    for i, st in enumerate(lut):
        next_start = st.start

        if next_start > cur_time:
            # st is our next state
            # we are currently in transition towards st

            # handle wrapping around 0
            if i is 0:
                prev_index = len(lut) - 1
            else:
                prev_index = i - 1

            pv_st = lut[prev_index]

            cond_print('currently in state:        '+str(pv_st.name))
            cond_print('current state start time:  ' + str(pv_st.start))
            cond_print('cur_time:                  '+str(cur_time))
            cond_print('next state start time:     ' + str(next_start))

            # calculate how far we are into the current state
            time_in = cur_time - pv_st.start
            cond_print('abs time in to this state: ' + str(time_in))

            # calculate what percentage we are into the current state
            frac_in = time_in / (next_start - pv_st.start)
            cond_print('frac in:                   ' + str(frac_in))

            # calculate interpolated hue
            prev_hue = pv_st.hue
            next_hue = st.hue
            cur_hue = frac_in * (next_hue - prev_hue) + prev_hue
            cond_print('cur_hue:                   ' + str(cur_hue))

            # calculate interpolated saturation
            prev_sat = pv_st.sat
            next_sat = st.sat
            cur_sat = frac_in * (next_sat - prev_sat) + prev_sat
            cond_print('cur_sat:                   '+str(cur_sat))

            # calculate interpolated brightness
            prev_bright = pv_st.bright
            next_bright = st.bright
            cur_bright = frac_in * (next_bright - prev_bright) + prev_bright
            cond_print('cur_bright:                '+str(cur_bright))

            # calculate interpolated kelvin
            prev_kelvin = pv_st.kelvin
            next_kelvin = st.kelvin
            cur_kelvin = int(frac_in *
                             (next_kelvin - prev_kelvin) + prev_kelvin)
            cond_print('cur_kelvin:                '+str(cur_kelvin))

            # calculate remaining duration in current state
            dur = next_start - cur_time
            dur_secs = day_frac_to_secs(dur)
            cond_print('dur secs remaining:        ' + str(dur_secs))

            # switch on at current pro-rated settings over 1s
            set_all_to_hsbk(cur_hue, cur_sat, cur_bright,
                            cur_kelvin, SWITCH_ON_FADEIN)
            time.sleep(SWITCH_ON_FADEIN)
            set_all_to_hsbk(st.hue, st.sat, st.bright, st.kelvin, dur_secs)
            break

def switch_off():
    global lights_on
    lights_on = False
    c_s = str('brightness:0.0')
    put_request(c_s, SWITCH_OFF_FADEOUT)
    print('switching off')

def put_request(c_s, duration):
    """ take a formatted color string and duration float
    and put that request to the LIFX API """
    cond_print('put request: {}, {}'.format(c_s, duration))
    data = json.dumps(
        {'selector':'all',
         'power':'on',
         'color':c_s,
         'duration':duration,
        })
    r = requests.put(STATE_URL, data, headers=lifx_api_creds.headers)
    print (r)

def set_all_to_hsbk(hue, saturation, brightness, kelvin, duration):
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
    put_request(c_s, duration)

def load_file():
    with open('data.json') as data_file:
        return json.load(data_file)
#    pprint(data)

def build_lut(data):
    states = data['states']
    lut = []
    for s in states:
        ls = LightState(s['name'], s['bright'], s['start'], s['hue'], s['sat'],
                        kelvin=s['kelvin'])
        lut.append(ls)
    return lut

def localize_lut(lut):
    sunrise, sunset, noon, twilight = sun_events()
    loc_lut = lut
    for st in loc_lut:
        if st.name == 'sunrise':
            st.start = datetime_to_day_frac(sunrise)
        elif st.name == 'sunset':
            st.start = datetime_to_day_frac(sunset)
        elif st.name == 'noon':
            st.start = datetime_to_day_frac(noon)
        elif st.name == 'twilight':
            st.start = datetime_to_day_frac(twilight)
    return loc_lut

def sort_lut(lut):
    return sorted(lut, key=lambda st: st.start)

def sun_events():
    o = ephem.Observer()
    o.horizon = '-0:34' # navy almanac
    o.pressure= 0
    o.lat = str(DATA['lat'])
    o.long = str(DATA['long'])
    sun = ephem.Sun()
    sun.compute()

    if DATA['extended-sunlight-mode']:
        o.date = "2015-06-21 00:00:00"
        print 'EXTENDED SUNLIGHT MODE'

    next_rising = o.next_rising(sun)
    next_rise_time = ephem.localtime(next_rising)
    cond_print('next_rising:  ' + str(next_rise_time))
    next_noon_time = ephem.localtime(o.next_transit(sun, start=next_rising))
    cond_print('next_noon: ' + str(next_noon_time))
    beg_twilight = ephem.localtime(o.previous_rising(ephem.Sun(),
                                                     use_center=True))
                                                     #Begin civil twilight
    next_set_time = ephem.localtime(o.next_setting(sun))
    cond_print('next_setting: ' + str(next_set_time))
    # if extended-daylight, add time after sundown
    return next_rise_time, next_set_time, next_noon_time, beg_twilight

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

#def onExit():
#    print 'IM BACK MUTHAFUCK: '


test_connection()

DATA = load_file()
VERBOSE = DATA['verbose']
SWITCH_ON_FADEIN = DATA['switch_on_fadein']
SWITCH_OFF_FADEOUT = DATA['switch_off_fadeout']
LIFX_URL = DATA['LIFX_URL']
STATE_URL = DATA['STATE_URL']

LOC_LUT = sort_lut(localize_lut(build_lut(DATA)))

while True:
    try:
        print 'checking'
        switch_on_from(LOC_LUT)
        # if current time > 
        time.sleep(240)
    except (KeyboardInterrupt, SystemExit):
        print 'quitting'
        raise

#CONSIDER DOING A BREATHE EFFECT FOR EASE-IN EASE-OUT



#print 'next sunrise: ', next_rise.time()

#tz = pytz.timezone('US/Eastern')
# 1. get correct date for the midnight using given timezone.
#today = datetime.datetime.now(tz).date()
# 2. get midnight in the correct timezone (taking into account DST)
#NOTE: tzinfo=None and tz.localize()
# assert that there is no dst transition at midnight (`is_dst=None`)
#midnight = tz.localize(datetime.datetime.combine(today, time(0, 0)), is_dst=None)
#print 'midnight: ', midnight
#print next_set.timedelta(midnight).seconds()

#today_length = next_rise - next_set

#print( next_rise.timetuple().tm_hour )

print 'LOC LUT: ', LOC_LUT
switch_on_from(LOC_LUT)

