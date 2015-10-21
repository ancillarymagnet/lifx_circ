# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 13:08:21 2015

@author: handsheik
"""
import json

def load_data():  
    with open('user_data.json') as data_file:    
        return json.load(data_file)
        
def generate_token():
    return load_data()['token']
    
def generate_headers():
    global token    
    return {"Authorization": "Bearer %s" % token}
    
token = generate_token()
print 'token generated: ', token
headers = generate_headers()
print 'headers generated: ', headers