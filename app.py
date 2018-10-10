#
# Copyright 2018 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import base64
import numpy as np
import requests
import json
import cv2
from flask import Flask, render_template, Response
from gevent import monkey
from io import BytesIO
from PIL import Image
try:
    from flask.ext.socketio import SocketIO, emit
except ImportError:
    from flask_socketio import SocketIO, emit
try:
    import Queue as queue
except ImportError:
    import queue

monkey.patch_all()
app = Flask(__name__)
app.config.from_object('config')
app.queue = queue.Queue()
socketio = SocketIO(app)


def draw_label(image, point, label, font=cv2.FONT_HERSHEY_SIMPLEX,
               font_scale=1, thickness=2):
    size = cv2.getTextSize(label, font, font_scale, thickness)[0]
    x, y = point
    cv2.rectangle(image, (x, y - size[1]), (x + size[0], y),
                  (255, 0, 0), cv2.FILLED)
    cv2.putText(image, label, point, font, font_scale,
                (255, 255, 255), thickness)


def base64_to_pil_image(base64_img):
    return Image.open(BytesIO(base64.b64decode(base64_img)))


@app.route("/")
def index():
    """Video streaming home page."""
    return render_template('index.html')


@socketio.on('netin', namespace='/streaming')
def msg(dta):
    emit('response', {'data': dta['data']})


@socketio.on('connected', namespace='/streaming')
def connected():
    emit('response', {'data': 'OK'})


@socketio.on('streamingvideo', namespace='/streaming')
def webdata(dta):
    app.queue.put(dta['data'])


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def gen():
    skip_frame = 1
    img_idx = 0

    while True:
        input_img = base64_to_pil_image(app.queue.get().split('base64')[-1])
        input_img.save("t1.jpg")

        img_idx += 1
        if img_idx % skip_frame == 0:
            img_pil = np.asarray(Image.open('t1.jpg'))

            img_h, img_w, _ = np.shape(img_pil)

            img_np_frame = img_pil

            img_np_frame = cv2.resize(img_np_frame,
                                      (1024, int(1024*img_h/img_w)))
            img_h, img_w, _ = np.shape(img_np_frame)

            my_files = {'image': open('t1.jpg', 'rb'),
                        'Content-Type': 'multipart/form-data',
                        'accept': 'application/json'}

            r = requests.post('http://localhost:5000/model/predict',
                              files=my_files, json={"key": "value"})

            json_str = json.dumps(r.json())
            data = json.loads(json_str)

            ret_res = data['predictions']

            if len(data['predictions']) <= 0:
                cv2.imwrite('t1.jpg', img_np_frame)
                yield (b'--img_np_frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n'
                       + open('t1.jpg', 'rb').read() + b'\r\n')
            else:
                for i in range(len(ret_res)):
                    age = ret_res[i]['age_estimation']
                    bbx = ret_res[i]['face_box']

                    # draw results
                    x1, y1, w, h = bbx
                    label = "{}".format(age)
                    draw_label(img_np_frame, (int(x1), int(y1)), label)

                    x2 = x1 + w
                    y2 = y1 + h
                    cv2.rectangle(img_np_frame, (int(x1), int(y1)),
                                  (int(x2), int(y2)), (0, 255, 255), 2)

            img_np_frame = cv2.cvtColor(img_np_frame, cv2.COLOR_BGR2RGB)
            cv2.imwrite('t1.jpg', img_np_frame)
            fh = open("./t1.jpg", "rb")
            frame = fh.read()
            fh.close()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            continue


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=7000)
