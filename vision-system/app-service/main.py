#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May 27 13:54:06 2023

@author: shervin
"""
from flask import Flask, render_template, Response
import cv2 as cv
import time
import numpy as np
from modules.redis_connector import RedisConnector



app = Flask(__name__)
redis = RedisConnector()

def gen_frames(): 
    while True:
        try:
            frame = redis.Unit8FromRedis('stream')
        except Exception as e:
            print('error: ',e)
            frame = np.zeros(shape=(480,640,3),dtype='uint8')
        ret, buffer = cv.imencode('.jpg',frame)
        frame = buffer.tobytes()
        
        yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n'+ frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run()
    
