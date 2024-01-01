#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 26 17:38:29 2023

@author: shervin
"""
from modules.helper import *


class ConfigLoader:
    def __init__(self,config_folder='configs'):
        self.general_configs_path = path.join(config_folder,'config.json')
        self.stereo_calibration_path = path.join(config_folder,'stereo_calibration.json')
        self.stereoSGM_path = path.join(config_folder,'stereoSGM_config.json')
        self.size_and_distance_model_path = path.join(config_folder,'size_and_distance_model.pt')
        
    def load_configs(self):
        
        log('Config Loader','Loading general configs...')
        config = open(self.general_configs_path)
        config = json.loads(config.read())
        self.config = config
        log('Config Loader','General configs loaded.')
        
        log('Config Loader','Loading stereo calibration data...')
        config = open(self.stereo_calibration_path)
        config = json.loads(config.read())
        self.calibration_data = config
        log('Config Loader','Stereo Calibration data loaded.')
        
        log('Config Loader','Loading stereoSGM configs...')
        config = open(self.stereoSGM_path)
        config = json.loads(config.read())
        self.stereoSGM_data = config
        log('Config Loader','StereoSGM configs loaded.')
        
        return self.config, self.calibration_data, self.stereoSGM_data
    


