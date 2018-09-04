#!/usr/bin/env python

from flask import Flask, render_template, Response
import cv2

from flask_restplus import Namespace, Resource, fields
import requests
import json
import numpy as np

app = Flask(__name__)
vc = cv2.VideoCapture(0)
vc.set(cv2.CAP_PROP_FRAME_WIDTH, 1024 * 1)
vc.set(cv2.CAP_PROP_FRAME_HEIGHT, 768 * 1)

api = Namespace('model', description='Model information and inference operations')

@app.route('/')
def index():
    return render_template('index.html')

#"Video streaming"
@app.route('/video_feed')
def video_feed():
    return Response(gen2(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def draw_label(image, point, label, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=1, thickness=2):
    size = cv2.getTextSize(label, font, font_scale, thickness)[0]
    x, y = point
    cv2.rectangle(image, (x, y - size[1]), (x + size[0], y), (255, 0, 0), cv2.FILLED)
    cv2.putText(image, label, point, font, font_scale, (255, 255, 255), thickness)


def gen2():
    """Video streaming generator function."""
    skip_frame=1
    img_idx = 0
    while True:
        img_idx=img_idx+1
        if img_idx%skip_frame==0:
            rval, frame = vc.read()

            img_h, img_w, _ = np.shape(frame)
            frame = cv2.resize(frame, (1024, int(1024*img_h/img_w)))
            img_h, img_w, _ = np.shape(frame)
            cv2.imwrite('t.jpg', frame)
            my_files = {'file': open('t.jpg', 'rb'), 'Content-Type': 'multipart/form-data',
                        'accept': 'application/json'}
            r = requests.post('http://localhost:5000/model/predict', files=my_files , json={"key": "value"})

            json_str = json.dumps(r.json())
            data = json.loads(json_str)

            ret_res=data['predictions']
            if len(data['predictions']) <=0:
                cv2.imwrite('t1.jpg', frame)

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + open('t1.jpg', 'rb').read() + b'\r\n')
            else:
                age=ret_res[0]['AGE_Estimation']
                bbx=ret_res[0]['Face_Box']
                print(age)
                print(bbx)

                for i in range(len(age)):
                    x1, y1, w, h = bbx
                    label = "{}".format(age[i])
                    draw_label(frame, (int(x1), int(y1)), label)
                    x2 = x1 + w
                    y2 = y1 + h
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                    # xw1 = max(int(x1 - 0.4 * w), 0)
                    # yw1 = max(int(y1 - 0.4 * h), 0)
                    # xw2 = min(int(x2 + 0.4 * w), img_w - 1)
                    # yw2 = min(int(y2 + 0.4 * h), img_h - 1)
                    # cv2.rectangle(frame, (xw1, yw1), (xw2, yw2), (255, 0, 0), 2)

            cv2.imwrite('t1.jpg', frame)

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + open('t1.jpg', 'rb').read() + b'\r\n')

        else:
            continue

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000, debug=True, threaded=True)
