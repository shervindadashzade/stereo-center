#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 31 19:30:55 2023

@author: shervin
"""
import redis
import numpy as np
import json
import struct
from os import path
from modules.helper import log

class RedisConnector:
    def __init__(self,config_folder='configs'):
        config = open(path.join(config_folder, 'config.json'))
        config = json.loads(config.read())
        log('Redis Connector','Connecting to redis...')
        try:
            self.redis = redis.Redis(host=config['redis']['host'],port=config['redis']['port'])
            log('Redis Connector','Connected to redis successfully.')
        except Exception as e:
            log(f'Redis Connector','Following error occured while trying to connect to redis. {e}')
    
    def Uint8ToRedis(self,array,key):
        h,w,c = array.shape
        
        shape = struct.pack('>III',h,w,c)
        encoded = shape + array.tobytes()
        self.redis.set(key,encoded)

    def Unit8FromRedis(self,key):
        encoded = self.redis.get(key)
        h,w,c = struct.unpack('>III', encoded[:12])
        
        a = np.frombuffer(encoded[12:],dtype='uint8').reshape(h,w,c)
        return a
        