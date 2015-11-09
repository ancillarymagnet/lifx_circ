# -*- coding: utf-8 -*-
"""
Created on Fri Oct 16 08:36:28 2015

@author: handsheik

TO DO:
• HTTP SERVER / SWITCH
• AUTO - FIRE NEXT CUE
• SUNRISE / SET RESET AT MIDNIGHT?
"""

import json
import logging
import logging.handlers
import requests
import time

import tornado.websocket
import tornado.httpserver
import tornado.ioloop

import config
import creds
import convert
from lightstate import LightState


LOG_FILENAME = 'logs/lifx_circ_trig.log'
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
        logger.info('new connection to switch, sending power state')
        msg = controller_pwr_msg()
        self.write_message(msg)
        CONTROLLERS.append(self)

    def on_message(self, message):
        logger.info('SWITCH message received: {msg}'.format(msg=message))
        if message == 'ON' or message == 'on':
            switch_on(True)
        elif message == 'OFF' or message == 'off':
            switch_off(True)
        else:
            logger.info('UNUSABLE MESSAGE FROM SWITCH')

    def on_close(self):
        logger.info('connection closed')
        CONTROLLERS.remove(self)

    def check_origin(self, origin):
        return True

def controller_pwr_msg():
    return "{ \"power_on\": \"%s\" }" % (lights_on)
    
def update_controller_pwr_states():
    for c in CONTROLLERS:
        c.write_message(controller_pwr_msg())

def test_connection():
    response_json = get_states()
    logger.info('TESTING.......')
    logger.info('-----------------')
    light_num = 0
    for r in response_json:
        logger.info('-------- LIGHT NUM: ' + str(light_num) + ' ---------')
        logger.info('-------- NAME: ' + str(r[u'label']) + ' --------')
        logger.info('-------- COLOR: ' + str(r[u'color']) + ' ---------')
        logger.info('-------- BRIGHT: ' + str(r[u'brightness']) + ' ---------')
        logger.info('-------- POWER:  ' + r[u'power'] + ' ---------')
        logger.info('///////////')
        light_num += 1
    logger.debug(power_state())

def get_states():
    response = requests.get(ALL_API_URL,
                            headers=creds.headers)
    return json.loads(response.text)

def power_state():
    response_json = get_states()
    return response_json[1][u'power']
    
def update_lights_on():
    global lights_on    
    if power_state() == "on":
        lights_on = True
    else:
        lights_on = False

def update_from(lut):
    cur_time = convert.secs_to_day_frac(convert.secs_into_day())
    logger.debug(convert.time_from_day_frac(cur_time))

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

            logger.debug('currently in state:        '+str(pv_st.name))
            logger.debug('current state start time:  ' + str(pv_st.start))
            logger.debug('cur_time:                  '+str(cur_time))
            logger.debug('next state start time:     ' + str(next_start))

            # calculate how far we are into the current state
            time_in = cur_time - pv_st.start
            logger.debug('abs time in to this state: ' + str(time_in))

            # calculate what percentage we are into the current state
            frac_in = time_in / (next_start - pv_st.start)
            logger.debug('frac in:                   ' + str(frac_in))

            # calculate interpolated hue
            cur_hue = frac_in * (st.hue - pv_st.hue) + pv_st.hue
            logger.debug('cur_hue:                   ' + str(cur_hue))

            # calculate interpolated saturation
            cur_sat = frac_in * (st.sat - pv_st.sat) + pv_st.sat
            logger.debug('cur_sat:                   '+str(cur_sat))

            # calculate interpolated brightness
            if lights_on:
                cur_bright = frac_in * (st.bright - pv_st.bright) + pv_st.bright
                logger.debug('cur_bright:                '+str(cur_bright))
                next_bright = st.bright
            else:
                cur_bright = 0.0
                next_bright = 0.0

            # calculate interpolated kelvin
            cur_kelvin = int(frac_in *
                             (st.kelvin - pv_st.kelvin) + pv_st.kelvin)
            logger.debug('cur_kelvin:                '+str(cur_kelvin))

            # calculate remaining duration in current state
            dur = next_start - cur_time
            dur_secs = convert.day_frac_to_secs(dur)
            logger.debug('dur secs remaining:        ' + str(dur_secs))

            # switch on at current pro-rated settings over 1s
            set_all_to_hsbk(cur_hue, cur_sat, cur_bright,
                            cur_kelvin, config.fade_in())
            time.sleep(config.fade_in())
            set_all_to_hsbk(st.hue, st.sat, next_bright, st.kelvin, dur_secs)
            break

def switch_off(from_controller):
    global lights_on
    lights_on = False
    c_s = str('brightness:0.0')
    put_request(c_s, config.fade_out())
    if from_controller:  
        logger.info('received power switch from controller, switching off')
    else:
        logger.info('notifying controller of power state switch off')
        update_controller_pwr_states()
    
def switch_on(from_controller):
    global lights_on
    lights_on = True
    update_from(LOC_LUT)
    if from_controller:  
        logger.info('received power switch from controller, switching on')
    else:
        logger.info('notifying controller of power state switch on')
        update_controller_pwr_states()

def put_request(c_s, duration):
    """ take a formatted color string and duration float
    and put that request to the LIFX API """
    logger.info('put request: {}, {}'.format(c_s, duration))
    data = json.dumps(
        {'selector':'all',
         'power':'on',
         'color':c_s,
         'duration':duration,
        })
    r = requests.put(config.state_url(), data, headers=creds.headers)
    logger.info(r)

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

def make_logger():
    logger = logging.getLogger('lifx_circ_trig')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.handlers.RotatingFileHandler(
                          LOG_FILENAME, maxBytes=50000, backupCount=5)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fh)
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)    
    return logger


logger = make_logger()
logger.info('<<<<<<<<<<<<<<<<<< SYSTEM RESTART >>>>>>>>>>>>>>>>>>>>>')

config.init()
LOC_LUT = config.LOC_LUT

test_connection()
update_lights_on()

application = tornado.web.Application(
    handlers=[
        (r"/", IndexHandler),
        (r"/ws", SwitchWSHandler),
    ])

http_server = tornado.httpserver.HTTPServer(application)
http_server.listen(PORT)
logger.info('*** Server listening on port {port} ****'.format(port=PORT))

tornado.ioloop.IOLoop.instance().start()

while True:
    try:
        print('mainloop')
        update_from(LOC_LUT)
        time.sleep(240)
    except (KeyboardInterrupt, SystemExit):
        logger.info('quitting')
        raise

#CONSIDER DOING A BREATHE EFFECT FOR EASE-IN EASE-OUT



