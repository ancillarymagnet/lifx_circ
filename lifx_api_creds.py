# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 13:08:21 2015

@author: handsheik
"""
import json

def load_data():  
    with open('user_data.json') as data_file:    
        return json.load(data_file)
        
def read_token():
    return load_data()['token']
    
def read_headers():
    global token    
    return {"Authorization": "Bearer %s" % token}
    
token = read_token()
headers = read_headers()