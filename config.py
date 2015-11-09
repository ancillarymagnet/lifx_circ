# -*- coding: utf-8 -*-
"""
Created on Sun Nov  8 12:42:54 2015

@author: handsheik
"""

import convert
import ephem
import json
from lightstate import LightState
import logging

def load_file():
    with open('data.json') as data_file:
        return json.load(data_file)

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
            st.start = convert.datetime_to_day_frac(sunrise)
        elif st.name == 'sunset':
            st.start = convert.datetime_to_day_frac(sunset)
        elif st.name == 'noon':
            st.start = convert.datetime_to_day_frac(noon)
        elif st.name == 'twilight':
            st.start = convert.datetime_to_day_frac(twilight)
    return loc_lut

def sort_lut(lut):
    return sorted(lut, key=lambda st: st.start)
    
def localize_and_sort(lut):
    return sort_lut(localize_lut(build_lut(lut)))

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
        logger.info('EXTENDED SUNLIGHT MODE')

    next_rising = o.next_rising(sun)
    next_rise_time = ephem.localtime(next_rising)
    logger.debug('next_rising:  ' + str(next_rise_time))
    next_noon_time = ephem.localtime(o.next_transit(sun, start=next_rising))
    logger.debug('next_noon: ' + str(next_noon_time))
    beg_twilight = ephem.localtime(o.previous_rising(ephem.Sun(),
                                                     use_center=True))
                                                     #Begin civil twilight
    next_set_time = ephem.localtime(o.next_setting(sun))
    logger.debug('next_setting: ' + str(next_set_time))
    # if extended-daylight, add time after sundown
    return next_rise_time, next_set_time, next_noon_time, beg_twilight

def verbose():
    return DATA['verbose']
    
def fade_in():
    return DATA['switch_on_fadein']
    
def fade_out():
    return DATA['switch_off_fadeout']

def lifx_url():
    return DATA['LIFX_URL']
    
def state_url():
    return DATA['STATE_URL']

def fetch_logger():
    global logger
    return logging.getLogger('lifx_circ_trig.config')

def init():
    global DATA
    global LOC_LUT
    global logger
    logger = fetch_logger()
    DATA = load_file()
    LOC_LUT = localize_and_sort(DATA)
