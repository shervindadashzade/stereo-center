#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 12 00:07:28 2023

@author: shervin
"""
import cv2 as cv
from datetime import datetime
import json
from os import path
import json
import glob

def log(scope,message):
    message = f'{scope}: {datetime.now()}: {message}'
    print(message)
    file = open('vision_system.log','a+')
    file.write(message+'\n')
    file.close()

def get_camera_capture(camera_id,width,height):
    capture = cv.VideoCapture(camera_id, cv.CAP_V4L2)
    capture.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    capture.set(cv.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv.CAP_PROP_FRAME_HEIGHT, height)
    return capture
