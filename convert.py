# -*- coding: utf-8 -*-
"""
Created on Sun Nov  8 17:03:22 2015

@author: handsheik
"""

import datetime
from math import floor

def secs_to_day_frac(secs):
    """ accepts seconds and returns TOD as fraction """
    if secs:
        return float(secs) / 86400
    else:
        return 0
        
def day_frac_to_secs(day_frac):
    """ accepts TOD as fraction and returns seconds """
    return float(day_frac) * 86400

def datetime_to_day_frac(dt):
    hrs = dt.time().hour
    mins = dt.time().minute
    secs = dt.time().second
    return secs_to_day_frac((hrs * 60 * 60) + (mins * 60) + secs)
    
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
    
def time_from_day_frac(day_frac):
    """ accepts TOD as fraction and returns time string as h:m:s """
    secs = day_frac_to_secs(day_frac)
    c_hr, c_min, c_sec = secs_to_hr_min_sec(secs)
    fmt_str = '{}:{}:{}'.format(c_hr, c_min, c_sec)
    return fmt_str
    
def interp(start, end, frac):
    return frac * (end - start) + start
    
def current_time():
    ct =  secs_to_day_frac(secs_into_day())
    return ct