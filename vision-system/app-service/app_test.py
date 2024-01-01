#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 26 19:01:05 2023

@author: shervin
"""

from modules.vision_utils import *
import time
from multiprocessing import Process, Queue
import multiprocessing
vision_util = VisionUtils()



def generate_depth_map(left_frame,right_frame,return_dict):
    depth_map = vision_util.generate_depth_map(left_frame, right_frame)
    return_dict['depth_map'] = depth_map


def process_a_frame(frame_queue):
    while True:
        try:
            frame = frame_queue.get_nowait()
            print('frame recieved.')
        except Exception as e:
            print(e)
            break
    
        vision_util.process_a_frame_using_yolo(frame)
        #print(result)
        print('frame proccessed.')
    

def process_frames():
    
    prev_frame_time = 0
    next_frame_time = 0
    
    while(True):
        ret, left_frame = left_cam.read()
        ret, right_frame = right_cam.read()
        
        left_frame, right_frame = vision_util.rectify_frames(left_frame, right_frame)
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        
        depth_map_process = Process(target=generate_depth_map, args=(left_frame,right_frame,return_dict))
        depth_map_process.start()
        
        vision_util.process_frames(left_frame, right_frame,RECTIFICATION_LINE=True)
        
        depth_map_process.join()
        
        
        next_frame_time = time.time()
        fps = float(1 / (next_frame_time - prev_frame_time))
        prev_frame_time = next_frame_time
        
    
        vision_util.show_fps(left_frame, fps)
        black_image = np.zeros(shape=(480,640,3),dtype='uint8')
        left_and_right_cameras = cv.hconcat([left_frame,right_frame])
        depth_map_and_black = cv.hconcat([return_dict['depth_map'],black_image])
        final_result = cv.vconcat([left_and_right_cameras,depth_map_and_black])
        cv.imshow('cameras',final_result)
        #cv.imshow('Left Camera',left_frame)
        #cv.imshow('Right Camera',right_frame)
        #cv.imshow('Depth Map',return_dict['depth_map'])
        key = cv.waitKey(1)
    
        if key==ord('q'):
            break
    
#%%


vision_util.load_models()



left_cam, right_cam = vision_util.load_cameras()
#%%
left_frame = cv.imread('bus.jpg')
frames = Queue()
for i in range(4):
    frames.put(left_frame)
#%%
proc = Process(target=process_a_frame, args=(frames,))
proc2 = Process(target=process_a_frame, args=(frames,))
proc2.start()
proc.start()
proc.join()
proc2.join()
#%%

proc = Process(target=process_frames())
proc.start()
proc.join()

#%%

prev_frame_time = 0
next_frame_time = 0

while(True):
    ret, left_frame = left_cam.read()
    ret, right_frame = right_cam.read()
    
    left_frame, right_frame = vision_util.rectify_frames(left_frame, right_frame)
    manager = multiprocessing.Manager()
    return_dict = manager.dict()
    
    depth_map_process = Process(target=generate_depth_map, args=(left_frame,right_frame,return_dict))
    depth_map_process.start()
    
    vision_util.process_frames(left_frame, right_frame,RECTIFICATION_LINE=True)
    
    depth_map_process.join()
    
    
    next_frame_time = time.time()
    fps = float(1 / (next_frame_time - prev_frame_time))
    prev_frame_time = next_frame_time
    

    vision_util.show_fps(left_frame, fps)
    black_image = np.zeros(shape=(480,640,3),dtype='uint8')
    left_and_right_cameras = cv.hconcat([left_frame,right_frame])
    depth_map_and_black = cv.hconcat([return_dict['depth_map'],black_image])
    final_result = cv.vconcat([left_and_right_cameras,depth_map_and_black])
    cv.imshow('cameras',final_result)
    #cv.imshow('Left Camera',left_frame)
    #cv.imshow('Right Camera',right_frame)
    #cv.imshow('Depth Map',return_dict['depth_map'])
    key = cv.waitKey(1)

    if key==ord('q'):
        break


cv.destroyAllWindows()
left_cam.release()
right_cam.release()