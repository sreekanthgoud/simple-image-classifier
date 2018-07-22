import os
import re
import uuid
import requests
import threading
import subprocess
import filetype

def is_jpeg(file):
    result = False
    file_type = filetype.guess(file).mime.lower().split('/')[1]

    if file_type in ['jpg', 'jpeg']:
        result = True

    return result

def save_from_bytes(file_bytes, dest_file):
    result = False
    if is_jpeg(file_bytes):
        with open(dest_file, 'wb') as file:
            file.write(file_bytes)
            result = True
    return result

def save_from_url(url, dest_file):
    result = False

    with open(dest_file, "wb") as f:
        response = requests.get(url)

        file = response.content
        if is_jpeg(file):
            f.write(file)
            result = True

    return result

def make_dir(directory):
    result = False
    if not os.path.exists(directory):
        os.makedirs(directory)
        result = True
    return result

def make_uuid():
    result = uuid.uuid4()
    return str(result)

def normalize_name(s):
    s = s.lower()
    s = re.sub(r"\s+", '_', s)
    return s

def train(dataset_path, training_steps):
    bottleneck_dir = dataset_path + 'bottlenecks'
    train_cmd = "python3.6 retrain.py "\
                "--bottleneck_dir={0} "\
                "--how_many_training_steps={1} "\
                "--output_graph={2}retrained_graph.pb "\
                "--output_labels={2}retrained_labels.txt "\
                "--image_dir {2}labels/".format(bottleneck_dir, training_steps, dataset_path)
    print(train_cmd)
    print(subprocess.check_output(train_cmd, shell=True))

def classify(dataset_path, request):
    filename = make_uuid() + '.jpg'
    filepath = dataset_path + '/' + filename

    # if url passed to json body
    try:
        request_json = request.json
    except:
        request_json = {}

    if 'url' in request_json.keys():
        save_from_url(request_json['url'], filepath)
    # if file passed in body
    else:
        save_from_bytes(request.body, filepath)

    results = []
    train_cmd = "python3.6 label.py "\
                "--output_layer=final_result "\
                "--input_layer=Placeholder "\
                "--graph={0}retrained_graph.pb "\
                "--labels={0}retrained_labels.txt "\
                "--image {1}".format(dataset_path, filepath)
    print(train_cmd)
    # very dirty part
    result = str(subprocess.check_output(train_cmd, shell=True))
    print(result)
    labels = result.split('### LABELS:')[1]
    labels = labels.split('LABEL: ')
    for l in labels:
        if len(l) > 2:
            accuracy = re.findall("\d+\.\d+", l)[0]
            accuracy = float(accuracy) * 100
            label = l.rstrip().split(' ->')[0]
            label = label.replace(' [', '').replace(']', '')
            data = {
                "label": label,
                "accuracy": accuracy
            }
            results.append(data)
    print(results)
    os.remove(filepath)
    return results


class Run(threading.Thread):

  def __init__(self, queue):
    threading.Thread.__init__(self)
    self.queue = queue

  def run(self):
    while True:
        task = self.queue.get()
        if task['action'] == 'train':
            print(task)
            dataset_path = task['dataset']['path']
            training_steps = int(task['training_steps'])
            train(dataset_path, training_steps)
        self.queue.task_done()