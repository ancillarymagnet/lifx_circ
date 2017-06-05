# -*- coding: utf-8 -*-
"""
Created on Mon Nov  9 10:52:58 2015

@author: handsheik
"""

import config
import logging
import websocket

SERV_PORT = '7777'
HOST = 'localhost'
URI = '/scheduler'

logger = logging.getLogger('lifx_circ_trig.scheduler')
logger.info('LAUNCHING SCHEDULER')

config.init()

websocket.enableTrace(True)
logger.info('attempting to connect to: ')
WS = websocket.create_connection('ws://' + str(HOST) + ':' + SERV_PORT + URI)


DATA = WS.recv()
if DATA:
    print 'CONNECTED TO SERVER: ', str(DATA)


WS.send('TRIGGER')


"""
while True:
    try:
        print('mainloop')
        update_from(config.LOC_LUT)
        time.sleep(240)
    except (KeyboardInterrupt, SystemExit):
        inf('quitting')
        raise
"""
