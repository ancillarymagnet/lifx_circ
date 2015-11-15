# -*- coding: utf-8 -*-
"""
@author: Noah Norman
n@hardwork.party
"""

class LightState(object):
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
