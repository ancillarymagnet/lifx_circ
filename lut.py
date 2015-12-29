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

DATA_PATH = 'lut.json'

class Lut(object):
    def __init__(self):
        self.data = self.__load_file()
        self.loc_lut = self.__localize_and_sort(self.data)

    def __repr__(self):
        rep = "///LUT: {}, ".format(self.loc_lut)
        return rep

    def __load_file(self):
        with open(DATA_PATH) as data_file:
            return json.load(data_file)

    def __localize_and_sort(self, lut):
        built_lut = self.__build_lut(lut)
        locd_lut = self.__localize_lut(built_lut)
        return self.__sort_lut(locd_lut)

    @staticmethod
    def __build_lut(data):
        states = data['states']
        lut = []
        for s in states:
            ls = LightState(s['name'], s['bright'], s['start'], s['hue'], s['sat'],
                            kelvin=s['kelvin'])
            lut.append(ls)
        return lut

    def __localize_lut(self, lut):
        sunrise, sunset, noon, twilight = self.__sun_events()
        localized_lut = lut
        for st in localized_lut:
            if st.name == 'sunrise':
                st.start = convert.datetime_to_day_frac(sunrise)
            elif st.name == 'sunrise-end':
                st.start = convert.datetime_to_day_frac(sunrise)
            elif st.name == 'sunset':
                st.start = convert.datetime_to_day_frac(sunset)
            elif st.name == 'noon':
                st.start = convert.datetime_to_day_frac(noon)
            elif st.name == 'twilight':
                st.start = convert.datetime_to_day_frac(twilight)
        return localized_lut

    @staticmethod
    def __sort_lut(lut):
        return sorted(lut, key=lambda st: st.start)

    def __sun_events(self):
        o = ephem.Observer()
        o.horizon = '-0:34' # navy almanac
        o.pressure = 0
        o.lat = str(self.data['lat'])
        o.long = str(self.data['long'])
        sun = ephem.Sun()
        sun.compute()

        if self.data['extended-sunlight-mode']:
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
        return next_rise_time, next_set_time, next_noon_time, beg_twilight

    def cur_state_index(self):
        cur_time = convert.current_time()
        for i, st in enumerate(self.loc_lut):
            if st.start > cur_time:
                return self.wrap_index(self.loc_lut, i - 1)
        return len(self.loc_lut) - 1

    @staticmethod
    def wrap_index(lst, i):
        if i > len(lst) - 1:
            i = 0
        elif i < 0:
            i = len(lst) - 1
        return i

    def state_now(self):
        cur_time = convert.current_time()
        st = self.loc_lut[self.cur_state_index()]
        nxt_st = self.next_state()

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

    def secs_to_next_state(self):
        cur_time = convert.current_time()
        nxt_st = self.next_state()
        # calculate remaining duration in current state
        if nxt_st.start < cur_time:
            # this would be in the event that we're in the last scene of the lut
            dur = (1 - cur_time) + nxt_st.start
        else:
            dur = nxt_st.start - cur_time
        t = convert.day_frac_to_secs(dur)
        dbg('secs to next state:        ' + str(t))
        return t

    def next_state(self):
        cur_index = self.cur_state_index()
        nxt_index = self.wrap_index(self.loc_lut, cur_index + 1)
        nxt_st = self.loc_lut[nxt_index]
        return nxt_st

    def refresh_solar(self):
        self.loc_lut = self.__localize_and_sort(self.data)


def inf(msg):
    LOGGER.info(msg)

def dbg(msg):
    LOGGER.debug(msg)

LOGGER = logging.getLogger('lct.lut')
