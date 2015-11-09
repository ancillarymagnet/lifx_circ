# -*- coding: utf-8 -*-
"""
Created on Fri Oct 16 08:36:28 2015

@author: handsheik

TO DO:
• HTTP BYPASS SWITCH
• AUTO - FIRE NEXT CUE
• SUNRISE / SET RESET AT MIDNIGHT?
• CONFIRM SWITCH RESPONSE
"""

import json
import requests
import time

import tornado.websocket
import tornado.httpserver
import tornado.ioloop

import config
import creds
import convert
import log

ALL_API_URL = 'https://api.lifx.com/v1/lights/all'
PORT = 7777
CONTROLLERS = []

class IndexHandler(tornado.web.RequestHandler):
    """HTTP request handler to serve HTML for switch server"""
    def get(self):
        self.render('switch/index.html')

class SwitchWSHandler(tornado.websocket.WebSocketHandler):
    """Communicates switch commands with the switch web view"""
    def open(self):
        inf('new connection to switch, sending power state')
        msg = controller_pwr_msg()
        self.write_message(msg)
        CONTROLLERS.append(self)

    def on_message(self, message):
        inf('SWITCH message received: {msg}'.format(msg=message))
        if message == 'ON' or message == 'on':
            switch_on(True)
        elif message == 'OFF' or message == 'off':
            switch_off(True)
        else:
            inf('UNUSABLE MESSAGE FROM SWITCH')

    def on_close(self):
        inf('connection closed')
        CONTROLLERS.remove(self)

    def check_origin(self, origin):
        return True

def controller_pwr_msg():
    return "{ \"power_on\": \"%s\" }" % (lights_on)
    
def update_controller_pwr_states():
    for c in CONTROLLERS:
        c.write_message(controller_pwr_msg())

def inf(str):
    logger.info(str)
    
def dbg(str):
    logger.debug(str)

def test_connection():
    response_json = get_states()
    inf('TESTING.......')
    inf('-----------------')
    light_num = 0
    for r in response_json:
        inf('-------- LIGHT NUM: ' + str(light_num) + ' ---------')
        inf('-------- NAME: ' + str(r[u'label']) + ' --------')
        inf('-------- COLOR: ' + str(r[u'color']) + ' ---------')
        inf('-------- BRIGHT: ' + str(r[u'brightness']) + ' ---------')
        inf('-------- POWER:  ' + r[u'power'] + ' ---------')
        inf('///////////')
        light_num += 1
    dbg(power_state())

def power_state():
    response_json = get_states()
    return response_json[1][u'power']
    
def get_states():
    response = requests.get(ALL_API_URL,
                            headers=creds.headers)
    return json.loads(response.text)
    
def interp(start, end, frac):
    return frac * (end - start) + start

def update_lights_on():
    global lights_on    
    if power_state() == "on":
        lights_on = True
    else:
        lights_on = False

def switch_off(from_controller):
    global lights_on
    lights_on = False
    c_s = str('brightness:0.0')
    if from_controller:  
        inf('received power switch from controller, switching off')
    else:
        inf('notifying controller of power state switch off')
        update_controller_pwr_states()
    put_request(c_s, config.fade_out())
    
def switch_on(from_controller):
    global lights_on
    lights_on = True
    if from_controller:  
        inf('received power switch from controller, switching on')
    else:
        inf('notifying controller of power state switch on')
        update_controller_pwr_states()
    update_from(config.LOC_LUT)

def update_from(lut):
    cur_time = convert.secs_to_day_frac(convert.secs_into_day())
    dbg(convert.time_from_day_frac(cur_time))

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

            dbg('currently in state:        '+str(pv_st.name))
            dbg('current state start time:  ' + str(pv_st.start))
            dbg('cur_time:                  '+str(cur_time))
            dbg('next state:                ' + str(st.name))
            dbg('next state start time:     ' + str(next_start))

            # calculate how far we are into the current state
            time_in = cur_time - pv_st.start
            dbg('abs time in to this state: ' + str(time_in))

            # calculate what percentage we are into the current state
            frac_in = time_in / (next_start - pv_st.start)
            dbg('frac in:                   ' + str(frac_in))

            cur_hue = interp(pv_st.hue, st.hue, frac_in)
            dbg('cur_hue:                   ' + str(cur_hue))

            cur_sat = interp(pv_st.sat, st.sat, frac_in)
            dbg('cur_sat:                   '+str(cur_sat))

            if lights_on:
                cur_bright = interp(pv_st.bright, st.bright, frac_in)
                next_bright = st.bright
            else:
                cur_bright = 0.0
                next_bright = 0.0
            dbg('cur_bright:                '+str(cur_bright))

            cur_kelvin = int(interp(pv_st.kelvin, st.kelvin, frac_in))
            dbg('cur_kelvin:                '+str(cur_kelvin))

            # calculate remaining duration in current state
            dur = next_start - cur_time
            dur_secs = convert.day_frac_to_secs(dur)
            dbg('dur secs remaining:        ' + str(dur_secs))

            # switch on at current pro-rated settings over 1s
            set_all_to_hsbk(cur_hue, cur_sat, cur_bright,
                            cur_kelvin, config.fade_in())
            time.sleep(config.fade_in())
            set_all_to_hsbk(st.hue, st.sat, next_bright, st.kelvin, dur_secs)
            break

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

def put_request(c_s, duration):
    """ take a formatted color string and duration float
    and put that request to the LIFX API """
    inf('put request: {}, {}'.format(c_s, duration))
    data = json.dumps(
        {'selector':'all',
         'power':'on',
         'color':c_s,
         'duration':duration,
        })
    r = requests.put(config.state_url(), data, headers=creds.headers)
    inf(r)


logger = log.make_logger()
inf('<<<<<<<<<<<<<<<<<< SYSTEM RESTART >>>>>>>>>>>>>>>>>>>>>')

config.init()
test_connection()
update_lights_on()

application = tornado.web.Application(
    handlers=[
        (r"/", IndexHandler),
        (r"/ws", SwitchWSHandler),
    ])

http_server = tornado.httpserver.HTTPServer(application)
http_server.listen(PORT)
inf('*** Server listening on port {port} ****'.format(port=PORT))

tornado.ioloop.IOLoop.instance().start()

while True:
    try:
        print('mainloop')
        update_from(config.LOC_LUT)
        time.sleep(240)
    except (KeyboardInterrupt, SystemExit):
        inf('quitting')
        raise

#CONSIDER DOING A BREATHE EFFECT FOR EASE-IN EASE-OUT



