import os
from flask import Flask
from queue import Queue
try:
    from flask.ext.socketio import SocketIO, emit
except ImportError:
    from flask_socketio import SocketIO, emit
from gevent import monkey
monkey.patch_all()

app = Flask(__name__)
app.config.from_object('config')
app.queue = Queue()
socketio = SocketIO(app)

from io import BytesIO
import base64
from PIL import Image
import numpy as np
from flask import Flask, render_template, Response
import requests
import json
import cv2
import scipy.stats as st

def conf_interval(age_array):
    res_conf_intval=st.t.interval(0.9, len(age_array)-1, loc=np.mean(age_array), scale=st.sem(age_array))
    return res_conf_intval

def draw_label(image, point, label, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=1, thickness=2):
    size = cv2.getTextSize(label, font, font_scale, thickness)[0]
    x, y = point
    cv2.rectangle(image, (x, y - size[1]), (x + size[0], y), (255, 0, 0), cv2.FILLED)
    cv2.putText(image, label, point, font, font_scale, (255, 255, 255), thickness)

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
    ebar_skip_frame=25
    ebar_frame_counter=0
    nm_frame2model=20
    img_idx = 0
    label_array = [[] for i in range(1)]
    label= ['']
    CI_flag=False

    ini_TK_flag = True
    tracker_failure=False
    init_ZERO_precidt=True
    tracker = cv2.MultiTracker_create()
    tracker2 = cv2.MultiTracker_create()

    while True:
        input_img = base64_to_pil_image(app.queue.get().split('base64')[-1])
        input_img.save("t3.jpg")

        img_idx+=1
        img_pil = np.asarray(Image.open('t3.jpg'))
        img_h, img_w, _ = np.shape(img_pil)
        img_np_frame=img_pil
        if img_idx % nm_frame2model == 0:
            # to get an update bbx
            if tracker_failure is True or ini_TK_flag is False:
                tracker = cv2.MultiTracker_create()
                ini_TK_flag = True
                tracker_failure=False
                init_ZERO_precidt=True

            my_files = {'image': open('t3.jpg', 'rb'), 'Content-Type': 'multipart/form-data',
                        'accept': 'application/json'}

            r = requests.post('http://localhost:5000/model/predict', files=my_files , json={"key": "value"})

            json_str = json.dumps(r.json())
            data = json.loads(json_str)

            ret_res=data['predictions']
            print("Sending every %d frames" %nm_frame2model)

        img_np_frame = cv2.resize(img_np_frame, (1024, int(1024*img_h/img_w)))
        img_h, img_w, _ = np.shape(img_np_frame)
        try:
            if len(data['predictions']) <=0:
                if init_ZERO_precidt is True:
                    trueOrfalse = tracker2.add(cv2.TrackerKCF_create(), img_np_frame, tuple(bbx))
                    init_ZERO_precidt=False
                # different to the First tracker; to avoid overlapped drawing
                tker_rst, boxes = tracker2.update(img_np_frame)
                if tker_rst:
                    trker_label_idx_empty_data = 0
                    for newbox in boxes:
                        p1 = (int(newbox[0]), int(newbox[1]))
                        p2 = (int(newbox[0] + newbox[2]), int(newbox[1] + newbox[3]))
                        draw_label(img_np_frame, (int(p1[0]), int(p1[1])), label[trker_label_idx_empty_data])
                        cv2.rectangle(img_np_frame, p1, p2, (255, 255, 0), 2, 1)
                        trker_label_idx_empty_data+=1
                        print(" Face detector failed => using tracking")

                cv2.imwrite('t1.jpg', img_np_frame)
                yield (b'--img_np_frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + open('t1.jpg', 'rb').read() + b'\r\n')

            else:
                if ebar_frame_counter+2>ebar_skip_frame or img_idx % nm_frame2model == 0:
                    label_array=[[] for i in range(len(ret_res))]
                    label=['']*len(ret_res)
                    ebar_frame_counter=0
                else:
                    ebar_frame_counter+=1
                for i in range(len(ret_res)):
                    # bbx is from 'face_cascade.detectMultiScale' lib
                    age = ret_res[i]['age_estimation']
                    bbx = ret_res[i]['face_box']
                    # only for 1st frame
                    if ini_TK_flag is True and i < len(ret_res):
                        ini_TK = tracker.add(cv2.TrackerKCF_create(), img_np_frame, tuple(bbx))
                    elif ini_TK_flag is False and tracker_failure is True:
                        ini_TK = tracker.add(cv2.TrackerKCF_create(), img_np_frame, tuple(bbx))
                        tracker_failure=False
                    # draw results
                    x1, y1, w, h = bbx
                    x2 = x1 + w
                    y2 = y1 + h
                    label_tmp = "{}".format(age)
                    label[i]= label_tmp.split('.')[0]
                    # get data for confidence interval
                    label_array[i].append(np.int(label[i]))
                    if len(label_array[i]) == ebar_skip_frame:
                        label_array_conf_intv=conf_interval(label_array[i])
                        try:
                            label_plus=int(label_array_conf_intv[0]-np.float64(label[i]))
                            label_mis=int(label_array_conf_intv[1]-np.float64(label[i]))
                        except:
                            label_plus=0
                            label_mis=0
                        label_a= int(sum(label_array[i]) / len(label_array[i])) + abs(label_plus)
                        label_b = int(sum(label_array[i]) / len(label_array[i])) - abs(label_mis)
                        if label_a==label_b:
                            label[i] = str(label_a)
                        elif label_a<label_b:
                            label[i]=str(label_a)+ '~' + str(label_b)
                        else:
                            label[i] = str(label_b) + '~' + str(label_a)
                    #     tmp_label=label[i]
                    #     CI_flag=True
                    # if CI_flag==True:
                    #     label[i]=tmp_label
                    if ini_TK_flag is True:
                        # draw label
                        draw_label(img_np_frame, (int(x1), int(y1)), label[i])
                        cv2.rectangle(img_np_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                        print("bbx and label from FACE DETECTOR")
                        tker_rst, boxes = tracker.update(img_np_frame)
                        # avoid overlap draw
                        init_ZERO_precidt=True
                        tracker2 = cv2.MultiTracker_create()

                    else:
                        print("Using tracking bbx")
                        # avoid overlap draw
                        init_ZERO_precidt=True
                        tracker2 = cv2.MultiTracker_create()

                        tker_rst, boxes = tracker.update(img_np_frame)
                        if tker_rst:
                            trker_label_idx = 0
                            for newbox in boxes:
                                p1 = (int(newbox[0]), int(newbox[1]))
                                p2 = (int(newbox[0] + newbox[2]), int(newbox[1] + newbox[3]))
                                draw_label(img_np_frame, (int(p1[0]), int(p1[1])), label[trker_label_idx])
                                cv2.rectangle(img_np_frame, p1, p2, (255, 255, 0), 2, 1)
                                trker_label_idx+=1
                        else:
                            tracker_failure=True
                            ini_TK_flag = False
                            print("TRACKER FAILURE..........")
                            break
                ini_TK_flag = False
        except:
            # the part only runs in the very beginning
            cv2.imwrite('t1.jpg', img_np_frame)
            yield (b'--img_np_frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + open('t1.jpg', 'rb').read() + b'\r\n')
        img_np_frame = cv2.cvtColor(img_np_frame, cv2.COLOR_BGR2RGB)
        cv2.imwrite('t1.jpg', img_np_frame)
        fh = open("./t1.jpg", "rb")
        frame = fh.read()
        fh.close()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=7000)
