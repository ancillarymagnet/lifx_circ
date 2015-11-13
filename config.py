# -*- coding: utf-8 -*-
"""
@author: Noah Norman
n@hardwork.party
"""

import ephem
import json

import convert
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
    o.pressure = 0
    o.lat = str(DATA['lat'])
    o.long = str(DATA['long'])
    sun = ephem.Sun()
    sun.compute()

    if DATA['extended-sunlight-mode']:
        o.date = "2015-06-21 00:00:00"
        inf('EXTENDED SUNLIGHT MODE')

    next_rising = o.next_rising(sun)
    next_rise_time = ephem.localtime(next_rising)
    dbg('next_rising:  ' + str(next_rise_time))
    next_noon_time = ephem.localtime(o.next_transit(sun, start=next_rising))
    dbg('next_noon: ' + str(next_noon_time))
    beg_twilight = ephem.localtime(o.previous_rising(ephem.Sun(),
                                                     use_center=True))
                                                     #Begin civil twilight
    next_set_time = ephem.localtime(o.next_setting(sun))
    dbg('next_setting: ' + str(next_set_time))
    # if extended-daylight, add time after sundown
    return next_rise_time, next_set_time, next_noon_time, beg_twilight

def cur_state_index():
    cur_time = convert.current_time()
    for i, st in enumerate(LOC_LUT):
        if st.start > cur_time:
            return wrap_index(LOC_LUT, i - 1)
    return len(LOC_LUT) - 1

def wrap_index(lst, i):
    if i > len(lst) - 1:
        i = 0
    elif i < 0:
        i = len(lst) - 1
    return i

def state_now():
    cur_time = convert.current_time()
    st = LOC_LUT[cur_state_index()]
    nxt_st = next_state()

    inf('currently in state:        ' + str(st.name))
    inf('current state start time:  ' + str(st.start))
    inf('cur_time:                  ' + str(cur_time))
    inf('next state:                ' + str(nxt_st.name))
    inf('next state start time:     ' + str(nxt_st.start))
    
    # calculate how far we are into the current state
    time_in = cur_time - st.start
    dbg('abs time in to this state: ' + str(time_in))

    # calculate what percentage we are into the current state
    frac_in = time_in / (nxt_st.start - st.start)
    dbg('frac in:                   ' + str(frac_in))

    cur_hue = convert.interp(st.hue, nxt_st.hue, frac_in)
    dbg('cur_hue:                   ' + str(cur_hue))

    cur_sat = convert.interp(st.sat, nxt_st.sat, frac_in)
    dbg('cur_sat:                   '+str(cur_sat))

    cur_bright = convert.interp(st.bright, nxt_st.bright, frac_in)
    dbg('cur_bright:                '+str(cur_bright))

    cur_kelvin = int(convert.interp(st.kelvin, nxt_st.kelvin, frac_in))
    dbg('cur_kelvin:                '+str(cur_kelvin))

    cur_st = LightState(st.name, cur_bright, st.start,
                        cur_hue, cur_sat, cur_kelvin)
    return cur_st

def secs_to_next_state():
    cur_time = convert.current_time()
    nxt_st = next_state()
    # calculate remaining duration in current state
    if nxt_st.start < cur_time:
        # this would be in the event that we're in the last scene of the lut
        dur = (1 - cur_time) + nxt_st.start
    else:
        dur = nxt_st.start - cur_time
    t = convert.day_frac_to_secs(dur)
    dbg('secs to next state:        ' + str(t))
    return t

def next_state():
    cur_index = cur_state_index()
    nxt_index = wrap_index(LOC_LUT, cur_index + 1)
    nxt_st = LOC_LUT[nxt_index]
#    nxt_nxt_index = wrap_index(LOC_LUT, nxt_index + 1)
#    nxt_nxt_st = LOC_LUT[nxt_nxt_index]
    # calculate duration of next state
#    if nxt_nxt_st.start < nxt_st.start:
#        # this would be in the event that the next is last scene of the lut
#        dur = (1 - nxt_st.start) + nxt_nxt_st.start
#    else:
#        dur = nxt_nxt_st.start - nxt_st.start
#    dur_secs = convert.day_frac_to_secs(dur)
    return nxt_st

def inf(msg):
    logger.info(msg)

def dbg(msg):
    logger.debug(msg)

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

def refresh_solar():
    global LOC_LUT
    LOC_LUT = localize_and_sort(DATA)

logger = logging.getLogger('lifx_circ_trig.config')
DATA = load_file()
LOC_LUT = localize_and_sort(DATA)
