# -*- coding: utf-8 -*-
"""
@author: Noah Norman
n@hardwork.party
"""

import json

def load_file():
    with open('data.json') as data_file:
        return json.load(data_file)

def verbose():
    return DATA['verbose']

def fade_in():
    return DATA['switch_on_fadein']

def fade_out():
    return DATA['switch_off_fadeout']

def lifx_url():
    return DATA['LIFX_URL']

def lights_url():
    return DATA['LIGHTS_URL']

DATA = load_file()
