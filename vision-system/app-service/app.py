#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May 27 23:29:19 2023

@author: shervin
"""
from modules.vision_utils import *
import time
from multiprocessing import Process, Queue, Manager
import multiprocessing
import numpy as np
import struct
from modules.redis_connector import RedisConnector
from modules.mongodb_connector import MongoDBConnector
import threading

def process_a_frame(result_dict, key):
    while(True):
        frame = result_dict[f'{key}_frame']
        if frame == 'stop':
            break
        result = vision_utils.process_a_frame_using_yolo(frame)
        result_dict[key] = result

def generate_depth_map(result_dict):
    while(True):
        if result_dict['left_frame'] == 'stop':
            break
        depth_map = vision_utils.generate_depth_map(result_dict['left_frame'], result_dict['right_frame'])
        result_dict['depth_map'] = depth_map

def adding_log_to_db():
    while(True):
        try:
            object_log = vision_utils.log_queue.get()
            if object_log == 'stop':
                break
            vision_utils.add_log_to_db(object_log)
        except:
            continue
    
vision_utils = VisionUtils()


is_model_loaded = vision_utils.load_models()

if is_model_loaded:
    left_cam, right_cam = vision_utils.load_cameras()
    
    mongodb_connector = MongoDBConnector()
    redis_connector = RedisConnector()
    
    
    prev_frame_time = 0
    next_frame_time = 0
    result_dict = Manager().dict()
    
    i = 0
    while True:
        _, left_frame = left_cam.read()
        _, right_frame = right_cam.read()
        
        left_frame, right_frame = vision_utils.rectify_frames(left_frame, right_frame)
        
        result_dict['left_frame'] = left_frame
        result_dict['right_frame'] = right_frame
        if i==0:
            # left frame process
            left_frame_proc = Process(target=process_a_frame,args=(result_dict,'left'))
            left_frame_proc.start()
            # right frame process
            right_frame_proc = Process(target=process_a_frame,args=(result_dict,'right'))
            right_frame_proc.start()
            # depth map process
            depth_map_proc = Process(target=generate_depth_map,args=(result_dict,))
            depth_map_proc.start()
            #start log threading
            log_thread = threading.Thread(target=adding_log_to_db)
            log_thread.start()
            i=1
        
        next_frame_time = time.time()
        fps = float(1 / (next_frame_time - prev_frame_time))
        prev_frame_time = next_frame_time
        vision_utils.show_fps(left_frame, fps)
        if 'left' in result_dict.keys() and 'right' in result_dict.keys():
            vision_utils.process_bboxes(result_dict['left'],result_dict['right'], left_frame, right_frame,RECTIFICATION_LINE=True)
        
        #cv.imshow('left_camera',left_frame)
        #cv.imshow('right_camera',right_frame)
        if 'depth_map' in result_dict.keys():
            tmp1 = cv.hconcat([left_frame,right_frame])
            tmp2 = cv.hconcat([result_dict['depth_map'], np.zeros(shape=(480,640,3),dtype='uint8')])
            stream = cv.vconcat([tmp1,tmp2])
            #cv.imshow('stream',stream)
            redis_connector.Uint8ToRedis(stream, 'stream')
        #key = cv.waitKey(1)
        
        #if key == ord('q'):
        #    result_dict['left_frame'] = 'stop'
        #    result_dict['right_frame'] = 'stop'
        #    vision_utils.log_queue.put('stop')
        #    break
        
    left_frame_proc.join()
    right_frame_proc.join()
    depth_map_proc.join()
    log_thread.join()
    
    left_cam.release()
    right_cam.release()
    cv.destroyAllWindows()
else:
    print('Error: Can not load the model....')
