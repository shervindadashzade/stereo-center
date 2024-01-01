#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  8 10:50:50 2023

@author: shervin
"""
import os
import json
from pymongo import MongoClient
from modules.helper import log
class MongoDBConnector:
    def __init__(self,config_folder='configs',db='Stereo_Center'):
        config_path = os.path.join(config_folder,'config.json')
        config = open(config_path)
        config = json.loads(config.read())
        config = config['mongo']
        log('MongoDBConnector',f'Connecting to MongoDB Server.')
        try:
            self.client = MongoClient(f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config['port']}")
            self.db = self.client[db]
            log('MongoDBConnector',f'Connected to MongoDB server successfully.')
        except Exception as e:
            log('MongoDBConnector',f'Can not connect to MongoDB: {e}')
    
    def get_db(self):
        return self.db
    
    def get_collection(self,collection_name):
        try:
            collection  = self.db[collection_name]
            return collection
        except Exception as e:
            log('MongoDBConnector',f'Can not get the collection {collection_name}: {e}')
