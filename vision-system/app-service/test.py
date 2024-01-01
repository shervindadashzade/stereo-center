import cv2 as cv
cam = cv.VideoCapture(6)
cam.read()
cam.release()
#%%

from modules.mongodb_connector import MongoDBConnector
import threading
import queue
from datetime import datetime
mongodb_connector = MongoDBConnector()
logs_collection  = mongodb_connector.get_collection('logs')

log_queue = queue.Queue()

def add_log_to_db_worker(q):
    while True:
        log = q.get()
        if log=='stop':
            return
        else:
            log['date'] = datetime.now()
            logs_collection.insert_one(log)

for i in range(20):
    log_queue.put({'test':'this is a test'})
log_queue.put('stop')

t = threading.Thread(target=add_log_to_db_worker,args=(log_queue,))
t.start()
t.join()
#%%
import requests
import zipfile

backend_url = "localhost:5000"

url = f"http://{backend_url}/api/v1/models/get_active_model"
response = requests.get(url)

if response.status_code == 200:
    # Extract the JSON data from the response
    json_data = response.json()
    
    model_file_url = f"http://{backend_url}{json_data['url']}"
    response = requests.get(model_file_url)
    if response.status_code == 200:
        #save model
        with open('models/model.zip',"wb") as file:
            file.write(response.content)
            zip_file =  'models/model.zip'
            folder_structure = [
                'yolov8n_openvino_model/',
                'yolov8n_openvino_model/yolov8n.bin',
                'yolov8n_openvino_model/yolov8n.xml',
                'yolov8n_openvino_model/metadata.yaml']
            with zipfile.ZipFile(zip_file,'r') as zip_ref:
                zip_info = zip_ref.infolist()
                files_to_extract = []
                for info in zip_info:
                    if info.filename in folder_structure:
                        files_to_extract.append(info)
                    
    else:
        print('Error',response.status_code)
    
    # Print the JSON response
    print(json_data)
else:
    # Request was not successful
    print("Error:", response.status_code)
    