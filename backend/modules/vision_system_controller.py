#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun  4 21:43:51 2023

@author: shervin
"""
import os
class VisionSystemController:
    def __init__(self):
        pass
    def start(self):
        os.system('echo Shervin1349 | sudo -S systemctl start vision-system')
    
    def stop(self):
        os.system('echo Shervin1349 | sudo -S systemctl stop vision-system')
    def restart(self):
        os.system('echo Shervin1349 | sudo -S systemctl restart vision-system')
