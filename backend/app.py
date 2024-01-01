#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 31 21:04:44 2023

@author: shervin
"""

from flask import Flask,jsonify, request, make_response, url_for, send_from_directory, Response
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity
import cv2 as cv
import numpy as np
import datetime
from pymongo import MongoClient
import hashlib
from flask_expects_json import expects_json
from jsonschema import ValidationError
from datetime import datetime as dt
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import os
from modules.redis_connector import RedisConnector
import psutil
import shutil
from flask_cors import CORS
from modules.vision_system_controller import VisionSystemController

client = MongoClient("mongodb://admin:pi*atJ0Y9E98@localhost")

db = client['Stereo_Center']
users_collection = db['users']
models_collection = db['models']
logs_collection = db['logs']
redis = RedisConnector()
vision_system_controller = VisionSystemController()

#%%
app = Flask(__name__)
jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = 'XVYOT50PE088WPBY2UPM56RRZ3HKM5OR0JBYI5WFN6394ENMDD8N715WM8YF'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=1)
app.config['PAGE_SIZE'] = 10
CORS(app)


UPLOAD_FOLDER = 'models'
ALLOWED_EXTENSIONS = {'zip'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
VISION_SYSTEM_FOLDER = '../vision-system/app-service'
app.config['VISION_SYSTEM_FOLDER'] = VISION_SYSTEM_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS



user_register_schema = {
    'type':'object',
    'properties': {
        'password': {'type':'string','mingLength':6, 'maxLength':60},
        'email': {'type':'string', 'format':'email'},
        'firstname':{'type':'string','minLength':3,'maxLength':60},
        'lastname': {'type':'string','minLength':3,'maxLength':60}
        },
    'required': ['password','email','firstname','lastname']
}


@app.route('/api/v1/users',methods=['POST'])
@expects_json(user_register_schema,check_formats=True)
def register():
    new_user = request.get_json()
    new_user['password'] = hashlib.sha256(new_user['password'].encode('utf-8')).hexdigest()
    doc = users_collection.find_one({'email':new_user['email']})
    if not doc:
        new_user['is_admin'] = False
        new_user['created_at'] = dt.now()
        new_user['updated_at'] = dt.now()
        new_user = { key: new_user[key] for key in ['password','email','is_admin','created_at','updated_at','firstname','lastname']}
        users_collection.insert_one(new_user)
        return jsonify({'msg':'User created successfully.'}), 201
    else:
        return jsonify({'msg':'Email already exists'}), 409



user_login_schema = {
    'type':'object',
    'properties':{
        'password': {'type':'string','mingLength':6, 'maxLength':60},
        'email': {'type':'string', 'format':'email'},
        },
    'required':['email','password']
}

@app.route('/api/v1/users/login',methods=['POST'])
@expects_json(user_login_schema,check_formats=True)
def login():
    login_details = request.get_json()
    user_from_db = users_collection.find_one({'email':login_details['email']})
    
    if user_from_db:
        encrypted_password = hashlib.sha256(login_details['password'].encode('utf-8')).hexdigest()
        if encrypted_password == user_from_db['password']:
            access_token = create_access_token(identity=user_from_db['email'])
            return jsonify(access_token=access_token), 200
    return jsonify({'msg':f'The email or password is incorrect.'}), 401



user_update_schema = {
    'type':'object',
    'properties': {
        'password': {'type':'string','mingLength':6, 'maxLength':60},
        'email': {'type':'string', 'format':'email'},
        'firstname':{'type':'string','minLength':3,'maxLength':60},
        'lastname': {'type':'string','minLength':3,'maxLength':60},
        'is_admin': {'type':'boolean'}
        },
}



@app.route('/api/v1/user',methods=['GET'])
@jwt_required()
def get_current_user_profile():
    current_user_email = get_jwt_identity()
    user_from_db = users_collection.find_one({'email':current_user_email})
    if not user_from_db:
        return jsonify({'msg':'Profile not found'}), 404

    user_from_db['_id'] = str(user_from_db['_id'])
    del user_from_db['password']
    return jsonify({'profile':user_from_db})


@app.route('/api/v1/users', methods=['GET'])
@jwt_required()
def get_all_users():
    current_user_email = get_jwt_identity()
    current_user_from_db = users_collection.find_one({'email':current_user_email})
    
    if not current_user_from_db:
        return jsonify({'msg':'Profile not found'}), 404
    
    if current_user_from_db['is_admin'] == True:
        all_users = users_collection.find({})
        users = []
        for user in all_users:
            user['_id'] = str(user['_id'])
            users.append(user)
        return jsonify(users), 200
    else:
        return jsonify({'msg':'You do not have access to this page.'}), 403


@app.route('/api/v1/users/<user_id>', methods=['GET','PUT','DELETE'])
@jwt_required()
@expects_json(user_update_schema,ignore_for=['GET','DELETE'],check_formats=True)
def get_user_profile(user_id):
    
    try:
        target_user = users_collection.find_one({'_id':ObjectId(user_id)})
    except:
        return jsonify({'msg':'Invalid user id.'}), 404
    if target_user is None:
        return jsonify({'msg':'Invalid user id.'}), 404
    
    current_user_email = get_jwt_identity()
    current_user_from_db = users_collection.find_one({'email':current_user_email})
    
    if not current_user_from_db:
        return jsonify({'msg':'Profile not found'}), 404
    
    if not (current_user_from_db['is_admin'] == True or target_user['email'] == current_user_from_db['email']):
        return jsonify({'msg':'You do not have access to this page.'}), 403
    
    
    if request.method == 'GET':
        target_user['_id'] = str(target_user['_id'])
        del target_user['password']
        return jsonify(target_user), 200
    
    elif request.method == 'PUT':
        user_details = request.get_json()
        if 'password' in user_details.keys():
            user_details['password'] = hashlib.sha256(user_details['password'].encode('utf-8')).hexdigest()
            target_user['password'] = user_details['password']
        if 'firstname' in user_details.keys():
            target_user['firstname'] = user_details['firstname']
        if 'lastname' in user_details.keys():
            target_user['lastname'] = user_details['lastname']
        if 'email' in user_details.keys():
            target_user['email'] = user_details['email']
        target_user['updated_at'] = dt.now()
        
        if 'is_admin' in user_details.keys():
            if current_user_from_db['is_admin'] == True:
                target_user['is_admin'] = user_details['is_admin']
            else:
                return jsonify({'msg':'You do not have access to alter is_admin field.'}), 403
        
        res = users_collection.update_one({'_id':target_user['_id']}, {'$set': target_user})
        print(res.modified_count)
        return jsonify({'msg': 'User updated successfully.'}), 200
    
    elif request.method == 'DELETE':
        res = users_collection.delete_one({'email':target_user['email']})
        if res.deleted_count == 1:
            return jsonify({'msg': 'User profile deleted successfully.'}), 200
        else:
            return jsonify({'msg':'Error occured while trying to delete user profile.'}), 401


@app.route('/api/v1/models',methods=['POST','GET'])
@jwt_required()
def upload_a_model():
    current_user_email = get_jwt_identity()
    user_from_db = users_collection.find_one({'email':current_user_email})
    if not user_from_db:
        return jsonify({'msg':'Profile not found'}), 404
    if user_from_db['is_admin'] == False:
        return jsonify({'msg':'You do not have access to this page.'}), 403
    
    if request.method == 'POST':
        if 'model' not in request.files:
            return jsonify({'msg':'The model field should be a file'}), 400
        file = request.files['model']
        
        if file.filename == '':
            return jsonify({'msg':'No model file has been selected.'}), 400
        if file and allowed_file(file.filename):
            if 'name' not in request.form:
                return jsonify({'msg':'Specify the name of the model.'}), 400
            name = request.form['name']
            if len(name) < 5 :
                return jsonify({'msg':'The model name should be more than 4 characters.'}), 400
            
            model_from_db = models_collection.find_one({'name':name})
            if model_from_db is not None:
                return jsonify({'msg':'This model name is already exists.'}), 400
            
            filename = secure_filename(name)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],name+'.zip'))
            url = url_for('download_model', name = name +'.zip')
            
            model = {
                'name':name,
                'url':url,
                'is_active':False,
                'uploaded_at':dt.now(),
                'uploaded_by': user_from_db['email']            
                }
            models_collection.insert_one(model)
            model['_id']= str(model['_id'])
            return jsonify({'msg':'Model uploaded successfully.','model':model}), 200        
        else:
            return jsonify({'msg':'Only zip extension is allowed.'}), 400
    elif request.method == 'GET':
        models_from_db = models_collection.find({})
        models = []
        for model in models_from_db:
            model['_id'] = str(model['_id'])
            models.append(model)
        return jsonify(models), 200
        


@app.route('/api/v1/models/<model_id>',methods=['GET','DELETE','PUT'])
@jwt_required()
def delete_and_activate_model(model_id):
    current_user_email = get_jwt_identity()
    user_from_db = users_collection.find_one({'email':current_user_email})
    if not user_from_db:
        return jsonify({'msg':'Profile not found'}), 404
    if user_from_db['is_admin'] == False:
        return jsonify({'msg':'You do not have access to this page.'}), 403

    try:
        target_model = models_collection.find_one({'_id':ObjectId(model_id)})
    except:
        return jsonify({'msg':'Invalid model id.'}), 404
    if target_model is None:
        return jsonify({'msg':'Invalid model id.'}), 404
    
    if request.method == 'GET':
        target_model['_id'] = str(target_model['_id'])
        return jsonify(target_model), 200
    
    if request.method == 'DELETE':
        model_path = os.path.join(app.config['UPLOAD_FOLDER'],target_model['name']+'.zip')
        try:
            os.remove(model_path)
            models_collection.delete_one({'name':target_model['name']})
            return jsonify({'msg':'Model has been deleted successfully.'}), 200
        except Exception as e:
            print(e)
            return jsonify({'msg':'An error occured while trying to remove model.'}), 400
    
    if request.method=='PUT':
        models_collection.update_many({}, {'$set':{'is_active':False}})
        models_collection.update_one({'name':target_model['name']}, {'$set':{'is_active':True}})
        return jsonify({'msg':'Model activated successfully, restart the system to use the new active model.'}), 200
  

@app.route('/api/v1/models/get_active_model',methods=['GET'])
def get_active_model():
    current_model = models_collection.find_one({'is_active':True})
    if current_model is None:
        return jsonify({'msg':'No active model has been found.'}), 400
    else:
        current_model['_id'] = str(current_model['_id'])
        return jsonify(current_model), 200
        
@app.route('/models_repo/<name>')
def download_model(name):
    return send_from_directory(app.config['UPLOAD_FOLDER'],name)




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

@app.route('/api/v1/system/video_feed')
def video_feed():
    #TODO:: add user authorizatin.
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/v1/system/stats',methods=['GET'])
@jwt_required()
def get_general_system_status():

    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory()[2]
    disk_usage = shutil.disk_usage('/')
    disk_usage = round((disk_usage[1]/disk_usage[0])* 100,2)
    is_active = 'running' if os.system('systemctl is-active --quiet vision-system')==0 else 'stopped'
    status = {
        'status': is_active,
        'cpu_usage':cpu_usage,
        'ram_usage':ram_usage,
        'disk_usage':disk_usage
        }
    return jsonify(status), 200

@app.route('/api/v1/system/log',methods=['GET'])
@jwt_required()
def get_system_log():
    try:
        file = open(os.path.join(app.config['VISION_SYSTEM_FOLDER'],'vision_system.log'))
        logs = file.readlines()[-30:]
    except Exception as e:
        log=''
        print(e)
    return jsonify({'logs':logs}), 200




@app.route('/api/v1/system/restart',methods=['GET'])
@jwt_required()
def restart():
    current_user_email = get_jwt_identity()
    user_from_db = users_collection.find_one({'email':current_user_email})
    if not user_from_db:
        return jsonify({'msg':'Profile not found'}), 404
    if user_from_db['is_admin'] == False:
        return jsonify({'msg':'You do not have access to this page.'}), 403
    
    vision_system_controller.restart()
    return jsonify({'msg':'Restarting system...'}), 200

@app.route('/api/v1/system/start',methods=['GET'])
@jwt_required()
def start():
    current_user_email = get_jwt_identity()
    user_from_db = users_collection.find_one({'email':current_user_email})
    if not user_from_db:
        return jsonify({'msg':'Profile not found'}), 404
    if user_from_db['is_admin'] == False:
        return jsonify({'msg':'You do not have access to this page.'}), 403
    
    vision_system_controller.start()
    return jsonify({'msg':'Starting System...'}), 200



@app.route('/api/v1/system/stop',methods=['GET'])
@jwt_required()
def stop():
    current_user_email = get_jwt_identity()
    user_from_db = users_collection.find_one({'email':current_user_email})
    if not user_from_db:
        return jsonify({'msg':'Profile not found'}), 404
    if user_from_db['is_admin'] == False:
        return jsonify({'msg':'You do not have access to this page.'}), 403
    
    vision_system_controller.stop()
    return jsonify({'msg':'System stopped.'}), 200

@app.route('/api/v1/system/object_logs',methods=['GET'])
@jwt_required()
def get_object_logs():
    current_user_email = get_jwt_identity()
    user_from_db = users_collection.find_one({'email':current_user_email})
    if not user_from_db:
        return jsonify({'msg':'Profile not found'}), 404
    page_size = app.config['PAGE_SIZE']
    logs_count = logs_collection.count_documents({})
    total_pages = int(logs_count / page_size)
    page_number = request.args.get('page_number')
    if page_number is None:
        page_number  = 1
    page_number = int(page_number)
    if page_number > total_pages:
        return jsonify({'error':f'Page number is more that total pages which is {total_pages}'}), 404
    
    logs = logs_collection.find({}).sort('date',-1).skip(page_size * (page_number - 1)).limit(page_size)
    logs_array = []
    for log in logs:
        log['_id'] = str(log['_id'])
        logs_array.append(log)
    
    return jsonify({'total_pages': total_pages, 'logs':logs_array}), 200
    


    

@app.errorhandler(400)
def bad_request(error):
    if isinstance(error.description, ValidationError):
        original_error = error.description
        return make_response(jsonify({'error': original_error.message}),400)
    return error


@app.route('/')
def hello_world():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()
    
