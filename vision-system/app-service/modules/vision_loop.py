#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 28 01:19:07 2023

@author: shervin
"""
from modules.vision_utils import *
import time
from multiprocessing import Process, Queue, Manager
import multiprocessing


class VisionSystem:
    
    def __init__(self):
        self.vision_utils = VisionUtils()
        self.vision_utils.load_models()
    
    def process_a_frame(self,result_dict, key):
        while(True):
            if f'{key}_frame' in result_dict.keys():
                frame = result_dict[f'{key}_frame']
                if frame == 'stop':
                    break
                result = self.vision_utils.process_a_frame_using_yolo(frame)
                result_dict[key] = result
            else:
                continue

    def generate_depth_map(self,result_dict):
        while(True):
            if 'left_frame' in result_dict.keys():
                if result_dict['left_frame'] == 'stop':
                    break
                depth_map = self.vision_utils.generate_depth_map(result_dict['left_frame'], result_dict['right_frame'])
                result_dict['depth_map'] = depth_map
            else:
                continue
    
    def vision_system_main_loop(self,shared_dict):
        
        
        left_cam, right_cam = self.vision_utils.load_cameras()
        
        
        prev_frame_time = 0
        next_frame_time = 0
        shared_dict['hi'] = True
        i=0
        while True:
            shared_dict['frame_count'] = i
            _, left_frame = left_cam.read()
            _, right_frame = right_cam.read()
            
            left_frame, right_frame = self.vision_utils.rectify_frames(left_frame, right_frame)
            
            shared_dict['left_frame'] = left_frame
            shared_dict['right_frame'] = right_frame
            
            next_frame_time = time.time()
            fps = float(1 / (next_frame_time - prev_frame_time))
            prev_frame_time = next_frame_time
            self.vision_utils.show_fps(left_frame, fps)
            if 'left' in shared_dict.keys() and 'right' in shared_dict.keys():
                self.vision_utils.process_bboxes(shared_dict['left'],shared_dict['right'], left_frame, right_frame,RECTIFICATION_LINE=True)
           
            #cv.imshow('left_camera',left_frame)
            #cv.imshow('right_camera',right_frame)
            if 'depth_map' in shared_dict.keys():
                tmp1 = cv.hconcat([left_frame,right_frame])
                tmp2 = cv.hconcat([shared_dict['depth_map'], np.zeros(shape=(480,640,3),dtype='uint8')])
                print('flask dict has been set')
                stream = cv.vconcat([tmp1,tmp2])
                shared_dict['stream'] = stream
                cv.imshow('stream',stream)
                
            key = cv.waitKey(1)
            i=i+1
            if key == ord('q'):
                shared_dict['left_frame'] = 'stop'
                shared_dict['right_frame'] = 'stop'
                break
        left_cam.release()
        right_cam.release()
        cv.destroyAllWindows()
