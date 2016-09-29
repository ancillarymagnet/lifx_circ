# -*- coding: utf-8 -*-
#!/usr/bin/env python

"""
lifx_bg.py 
a circadian light controller and interface for LIFX HTTP API v1
@author: Noah Norman
n@hardwork.party


TO DO:
• HTTP BYPASS SWITCH
• CONFIRM SWITCH RESPONSE
• ARGUMENTS / JSON in data.json FOR ALL or SPECIFIC LIGHT NAMES
"""

import json
import requests
import time

import socket
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
from tornado import gen

import log
import lut
import config
import creds

PORT = 8888
CONTROLLERS = []
LUT = lut.Lut();

class IndexHandler(tornado.web.RequestHandler):
    """HTTP request handler to serve HTML for switch server"""
    def get(self):
        self.render('switch/index.html')

class SwitchWSHandler(tornado.websocket.WebSocketHandler):
    """Communicates switch commands with the switch web view"""
    def open(self):
#        self.set_header("Access-Control-Allow-Origin", '*')
        inf('new connection to switch, sending power state')
        msg = controller_pwr_msg()
        self.write_message(msg)
        CONTROLLERS.append(self)

    def on_message(self, message):
        inf('SWITCH message received: {msg}'.format(msg=message))
        if message == 'ON' or message == 'on':
            switch('on', True)
        elif message == 'OFF' or message == 'off':
            switch('off', True)
        else:
            inf('UNUSABLE MESSAGE FROM SWITCH')

    def on_close(self):
        inf('connection closed')
        CONTROLLERS.remove(self)

    def check_origin(self, origin):
        return True

def controller_pwr_msg():
    return "{ \"power_on\": \"%s\" }" % (is_on())

def update_controller_pwr_states():
    for con in CONTROLLERS:
        con.write_message(controller_pwr_msg())

def inf(msg):
    logger.info(msg)

def dbg(msg):
    logger.debug(msg)

def test_connection():
    response_json = get_states()
    inf('TESTING.......')
    inf('-----------------')
    for num, rsp in enumerate(response_json):
        inf('-------- LIGHT NUM: ' + str(num) + ' ---------')
        inf('-------- NAME: ' + str(rsp[u'label']) + ' --------')
        inf('-------- COLOR: ' + str(rsp[u'color']) + ' ---------')
        inf('-------- BRIGHT: ' + str(rsp[u'brightness']) + ' ---------')
        inf('-------- POWER:  ' + rsp[u'power'] + ' ---------')
        inf('///////////')
    dbg(power_state())

def is_on():
    if power_state() == 'on':
        return True
    else:
        return False

def power_state():
    """ assumes all lights share the same state """
    response_json = get_states()
    return response_json[1][u'power']

def get_states():
    response = requests.get(config.lights_url(),
                            headers=creds.headers)
    return json.loads(response.text)

@gen.engine
def switch(pwr, from_controller):
    if from_controller:
        inf('received power switch from controller, switching {p}'.format(p=pwr))
    else:
        inf('notifying controller of power state switch {p}'.format(p=pwr))
        update_controller_pwr_states()
    c_st = LUT.state_now()
    if pwr == 'on':
        t = config.fade_in()
    else:
        t = config.fade_out()
    set_all_to_hsbkdp(c_st.hue, c_st.sat, c_st.bright,
                      c_st.kelvin, t, pwr)
    # that command broke the existing transition so we have to put a new one
    yield gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, time.time() + t)
    goto_next_state()

def goto_next_state():
    nxt_st = LUT.next_state()
    t = LUT.secs_to_next_state()

    inf('transitioning to:          ' + str(nxt_st.name))
    inf('over:                      ' + str(t))

    set_all_to_hsbkdp(nxt_st.hue, nxt_st.sat, nxt_st.bright, nxt_st.kelvin, t)
    go_next_in(t+1)


@gen.engine
def go_next_in(t):
    inf('WAITING {s}s TO NEXT TRANSITION'.format(s=t))
    yield gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, time.time() + t)
    goto_next_state()

def set_all_to_hsbkdp(hue, saturation, brightness, kelvin,
                      duration, pwr=None):
    if pwr == None:
        pwr = power_state()
    if pwr == 'off':
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
    put_request(c_s, pwr, duration)

def put_request(c_s, pwr, duration):
    """ take a formatted color string and duration float
    and put that request to the LIFX API """
    inf('**** put request: {}, {}, {}s'.format(c_s, pwr, duration))
    data = json.dumps(
        {'selector':'all',
         'power': pwr,
         'color': c_s,
         'duration': duration,
        })
    r = requests.put(config.state_url(), data, headers=creds.headers)
    inf(r)

logger = log.make_logger()
inf('<<<<<<<<<<<<<<<<<< SYSTEM RESTART >>>>>>>>>>>>>>>>>>>>>')

test_connection()

# update sunrise / sunset every day
MS_DAY = 60 * 60 * 24 * 1000
refresh_solar_info = tornado.ioloop.PeriodicCallback(LUT.refresh_solar(),                                                     MS_DAY)
refresh_solar_info.start()


switch('on', False)
print 'state now: ' + str(LUT.state_now())
print 'next state: ' + str(LUT.next_state())
print 'secs to next state: ' + str(LUT.secs_to_next_state())


application = tornado.web.Application(
    handlers=[
        (r"/", IndexHandler),
        (r"/ws", SwitchWSHandler),
    ])

http_server = tornado.httpserver.HTTPServer(application)
http_server.listen(PORT)
my_ip = socket.gethostbyname(socket.gethostname())
inf('*** Server Started at {ip} ***'.format(ip=my_ip))
inf('*** Server listening on port {port} ****'.format(port=PORT))

# if you want to cancel this, hang on to next_timeout for cancel_timeout
#next_timeout = tornado.ioloop.IOLoop.instance().add_timeout(
#    datetime.timedelta(seconds=5), begin_from(config.LOC_LUT))


tornado.ioloop.IOLoop.instance().start()



#CONSIDER DOING A BREATHE EFFECT FOR EASE-IN EASE-OUT



