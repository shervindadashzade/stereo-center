#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 26 17:55:08 2023

@author: shervin
"""
import cv2 as cv
import numpy as np
import torch
from ultralytics import YOLO
from modules.config_loader import ConfigLoader
from modules.size_model import SizeNet
from modules.helper import log, get_camera_capture
from ultralytics.yolo.utils.plotting import colors
import requests
import zipfile
import os
import glob
import shutil
import queue
from modules.mongodb_connector import MongoDBConnector
from datetime import datetime
import torch

class VisionUtils:
    def __init__(self):
        self.object_logs = []
        self.log_queue = queue.Queue()
        self.mongodb_connector = MongoDBConnector()
        self.logs_collection = self.mongodb_connector.get_collection('logs')
        self.left_cam = None
        self.right_cam = None
        log('VisionUtils','Starting System...')
        log('VisionUtils','Loading configs...')
        self.config_loader = ConfigLoader()
        self.config_loader.load_configs()
        log('VisionUtils','Configs loaded successfully.')
        
        log('VisionUtils','Initializing rectification module...')
        data = self.config_loader.calibration_data
        left_K = np.array(data['left_K'])
        left_D  = np.array(data['left_D'])
        right_K = np.array(data['right_K'])
        right_D = np.array(data['right_D'])
        R = np.array(data['R'])
        T = np.array(data['T'])
        E = np.array(data['E'])
        F = np.array(data['F'])
        
        WIDTH = self.config_loader.config['width']
        HEIGHT = self.config_loader.config['height']
        
        R1, R2, P1, P2, Q, roi_left, roi_right = cv.stereoRectify(left_K, left_D, right_K, right_D, (WIDTH, HEIGHT),
                                                   R, T, flags=cv.CALIB_ZERO_DISPARITY,
                                                   alpha=-1)
        
        self.left_MapX, self.left_MapY = cv.initUndistortRectifyMap(left_K, left_D, R1, P1, (WIDTH, HEIGHT), cv.CV_32FC1)
        
        self.right_MapX, self.right_MapY = cv.initUndistortRectifyMap(right_K, right_D, R2, P2,  (WIDTH, HEIGHT), cv.CV_32FC1)

        log('VisionUtils','Rectification module initialized.')       
        
        
        log('VisionUtils','Initializing StereoSGBM module...')
        
        data = self.config_loader.stereoSGM_data
        
        self.stereo_SGBM = cv.StereoSGBM_create(
        minDisparity = data['min_disp'],
        numDisparities = data['num_disp'],
        blockSize = data['window_size'],
        uniquenessRatio = data['uniquenessRatio'],
        speckleWindowSize = data['speckleWindowSize'],
        speckleRange = data['speckleRange'],
        disp12MaxDiff = data['disp12MaxDiff'],
        P1 = data['P1'],
        P2 = data['P2'],
        )
        
        log('VisionUtils','StereoSGBM module Initialized.')
        
        
        self.FONT = cv.FONT_HERSHEY_SIMPLEX
    
    def add_log_to_db(self,object_log):
        try:
            self.logs_collection.insert_many(object_log)
        except Exception as e:
            print(e)
    
    
    def download_model(self):
        models_files = glob.glob('models/*')
        if models_files != []:
            path = 'models/'
            shutil.rmtree(path)
        models_files = glob.glob('models/*')
        if models_files != []:
            os.rmdir('models')
        try:
            os.makedirs('models')
        except Exception as e:
            print(e)
        backend_url = self.config_loader.config['BACKEND_URL']
        get_model_details_url = f'http://{backend_url}/api/v1/models/get_active_model'
        resp = requests.get(get_model_details_url)
        log('VisionUtils','Getting Object Detection Model Info...')
        if resp.status_code == 200:
            model_detail = resp.json()
            log('VisionUtils','Downloading Object Detection Model...')
            self.model_name = model_detail['name']
            download_model_url = f"http://{backend_url}{model_detail['url']}"
            resp = requests.get(download_model_url)
            if resp.status_code == 200:
                model_path = 'models/model.zip'
                folder_structure = [
                    'yolov8n_openvino_model/',
                    'yolov8n_openvino_model/yolov8n.bin',
                    'yolov8n_openvino_model/yolov8n.xml',
                    'yolov8n_openvino_model/metadata.yaml']
                with open(model_path,'wb') as file:
                    file.write(resp.content)
                log('VisionUtils','Model downloaded successfully.')
                log('VisionUtils','Checking model file structure.')
                with zipfile.ZipFile(model_path) as zip_ref:
                    zip_info = zip_ref.infolist()
                    files_to_extract = []
                    for info in zip_info:
                        if info.filename in folder_structure:
                            files_to_extract.append(info)
                    if len(files_to_extract) != 4:
                        log('VisionUtils','Model file structure is not valid. use YOLOv8 OpenVino optimized model only.')
                        return False
                    for file in files_to_extract:
                        zip_ref.extract(file,'models/')
                    
                    log('VisionUtils','Model extracted successfully.')
                    return True
                
            else:
                log('VisionUtils','Can not download object detection model...')
                return False
            
        else:
            log('VisionUtils','No active model has been found.')
            return False
        
    
    def load_models(self):
        log('VisionUtils','Loading Object Detection Model...')
        res = self.download_model()
        if not res:
            return False
        ob_path = glob.glob('models/yolov8*')[0]
        self.yolo_model = YOLO(ob_path)
        log('VisionUtils','Object Detection model loaded successfully...')
        
        log('VisionUtils','Initializing the Size and Distance Model...')
        self.size_model = SizeNet()
        self.size_model.load_state_dict(torch.load('configs/size_and_distance_model.pt'))
        self.size_model.eval()
        log('VisionUtils','Size and Distance Model loaded successfully.')
        return True
        
    def load_cameras(self):
        if self.left_cam is None and self.right_cam is None:
            log('VisionUtils','Loading Left and Right camera streams...')
            config = self.config_loader.config
            width = config['width']
            height = config['height']
            try:
                self.left_cam = get_camera_capture(config['LEFT_CAM'], width, height)
                self.right_cam = get_camera_capture(config['RIGHT_CAM'], width, height)
            except Exception as e:
                log('VisionUtils',f'Error: There is an error while trying to load left and right cameras... \n {e}')
                return False
            
            
            log('VisionUtils','Both cameras streams loaded successfully.')
        
        return self.left_cam, self.right_cam
   
    
    def rectify_frames(self,left_frame,right_frame):
        left_frame = cv.remap(left_frame, self.left_MapX, self.left_MapY, cv.INTER_LINEAR, cv.BORDER_CONSTANT)
        right_frame = cv.remap(right_frame, self.right_MapX, self.right_MapY, cv.INTER_LINEAR, cv.BORDER_CONSTANT)
        return left_frame, right_frame
    
    def process_frames(self,left_frame,right_frame,RECTIFICATION_LINE=False):
        
        if RECTIFICATION_LINE:
            for i,y in enumerate(np.round(np.linspace(0,450,7)).astype(int)):
                color = colors(i)
                left_frame = cv.line(left_frame, (0,y),(1280,y),color,1)
                right_frame = cv.line(right_frame, (0,y),(1280,y),color,1)
                   
        
        FONT = self.FONT    
        disparity = None
        left_results = self.yolo_model.track(left_frame,conf=0.7)[0]
        right_results = self.yolo_model.track(right_frame,conf=0.7)[0]
        
        
        for left_box in left_results.boxes:
            left_class_id = int(left_box.cls.item())
            try:
                left_track_id  = int(left_box.id.item())
            except:
                left_track_id = 'left_?'
            
            for right_box in right_results.boxes:
               right_class_id = int(right_box.cls.item())
               try:
                   right_track_id  = int(right_box.id.item())
               except:
                   right_track_id = 'right_?'
               
               if left_class_id != right_class_id or left_track_id != right_track_id:
                   continue
               else:
                   class_name = left_results.names[left_class_id]
                   color = colors(left_class_id)
                   track_id = left_track_id
                   left_x1,left_y1,left_x2,left_y2 = left_box.xyxy.numpy().squeeze().astype(int).tolist()
                   right_x1,right_y1,right_x2,right_y2 = right_box.xyxy.numpy().squeeze().astype(int).tolist()

                   
                   disparity = abs((left_x1 + left_x2) / 2 - (right_x1 + right_x2) / 2)
                   avg_width = (abs((left_x1-left_x2)) + abs(right_x1 - right_x2) ) / 2
                   avg_height = (abs((left_y1-left_y2)) + abs(right_y1 - right_y2) ) / 2
                  
                   distance, width_coef,height_coef = self.size_model.predict(disparity)
                   width = avg_width * width_coef
                   height = avg_height * height_coef
                   
                   cv.putText(left_frame, f'{class_name}:{track_id}', (left_x1,left_y1),FONT, 1, color, 2, cv.LINE_AA)
                   cv.putText(left_frame, f'W:{width:.2f} cm H:{height:.2f} cm', (left_x1,left_y2 + 20),FONT, 1, color, 2, cv.LINE_AA)
                   cv.rectangle(left_frame, (left_x1,left_y1), (left_x2,left_y2), color, 2)
                   
                   
                   cv.putText(right_frame, f'{class_name}:{track_id}', (right_x1,right_y1),FONT, 1, color, 2, cv.LINE_AA)
                   cv.putText(right_frame, f'distance:{distance:.3f} cm',  (right_x1,right_y2 + 20),FONT, 1, color, 2, cv.LINE_AA)
                   cv.rectangle(right_frame, (right_x1,right_y1), (right_x2,right_y2), color, 2)
    
    def generate_depth_map(self,left_frame,right_frame):
        left_gray = cv.cvtColor(left_frame, cv.COLOR_BGR2GRAY)
        right_gray = cv.cvtColor(right_frame, cv.COLOR_BGR2GRAY)
        
        disparity = self.stereo_SGBM.compute(left_gray,right_gray).astype(np.float32) / 16.0
        disparity = (disparity-self.stereo_SGBM.getMinDisparity())/ self.stereo_SGBM.getNumDisparities()
        disparity = cv.normalize(disparity, None, 0, 255, cv.NORM_MINMAX, cv.CV_8U)
        heatmap = cv.applyColorMap(disparity, cv.COLORMAP_JET)
        print(heatmap.shape)
        return heatmap
    
    def show_fps(self,frame,fps):
        cv.putText(frame, f'FPS: {fps:.2f}', (50,50),self.FONT, 1,(0,0,255), 2, cv.LINE_AA)
        
    def process_a_frame_using_yolo(self,frame):
        result =self.yolo_model.track(frame,conf=0.7)[0]
        return result
        
    def process_bboxes(self,left_results,right_results,left_frame,right_frame,RECTIFICATION_LINE=False):
        
        if RECTIFICATION_LINE:
            for i,y in enumerate(np.round(np.linspace(0,450,7)).astype(int)):
                color = colors(i)
                left_frame = cv.line(left_frame, (0,y),(1280,y),color,1)
                right_frame = cv.line(right_frame, (0,y),(1280,y),color,1)

        
        FONT = self.FONT    
        disparity = None
        
        for left_box in left_results.boxes:
            left_class_id = int(left_box.cls.item())
            try:
                left_track_id  = int(left_box.id.item())
            except:
                left_track_id = 'left_?'
            
            for right_box in right_results.boxes:
               right_class_id = int(right_box.cls.item())
               try:
                   right_track_id  = int(right_box.id.item())
               except:
                   right_track_id = 'right_?'
               
               if left_class_id != right_class_id or left_track_id != right_track_id:
                   continue
               else:
                   class_name = left_results.names[left_class_id]
                   color = colors(left_class_id)
                   track_id = left_track_id
                   left_x1,left_y1,left_x2,left_y2 = left_box.xyxy.numpy().squeeze().astype(int).tolist()
                   right_x1,right_y1,right_x2,right_y2 = right_box.xyxy.numpy().squeeze().astype(int).tolist()

                   
                   disparity = abs((left_x1 + left_x2) / 2 - (right_x1 + right_x2) / 2)
                   avg_width = (abs((left_x1-left_x2)) + abs(right_x1 - right_x2) ) / 2
                   avg_height = (abs((left_y1-left_y2)) + abs(right_y1 - right_y2) ) / 2
        
                   distance, width_coef,height_coef = self.size_model([[disparity]]).detach().squeeze()
                   width = avg_width * width_coef.item()
                   height = avg_height * height_coef.item()
                   distance = distance.item()
                   
                   cv.putText(left_frame, f'{class_name}:{track_id}', (left_x1,left_y1),FONT, 1, color, 2, cv.LINE_AA)
                   cv.putText(left_frame, f'W:{width:.2f} cm H:{height:.2f} cm', (left_x1,left_y2 + 20),FONT, 1, color, 2, cv.LINE_AA)
                   cv.rectangle(left_frame, (left_x1,left_y1), (left_x2,left_y2), color, 2)
                   
                   
                   cv.putText(right_frame, f'{class_name}:{track_id}', (right_x1,right_y1),FONT, 1, color, 2, cv.LINE_AA)
                   cv.putText(right_frame, f'distance:{distance:.3f} cm',  (right_x1,right_y2 + 20),FONT, 1, color, 2, cv.LINE_AA)
                   cv.rectangle(right_frame, (right_x1,right_y1), (right_x2,right_y2), color, 2)
                   if len(self.object_logs) < 50:
                       object_log = {'width':width,'height':height,'distance':distance,'class_name':class_name,'object_id':class_name[:2].upper()+str(track_id)}
                       object_log['date'] = datetime.now()
                       object_log['model'] = self.model_name
                       self.object_logs.append(object_log)
                   else:
                       self.log_queue.put(self.object_logs)
                       self.object_logs = []
                       
                   
