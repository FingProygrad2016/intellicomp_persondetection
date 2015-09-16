import numpy as np
import cv2
import time
from datetime import datetime, timedelta
from black_boxes.background_substraction import BackgroundSubtractor
from black_boxes.blob_detection import BlobDetector
from black_boxes.tracking import Tracker


def do_the_thing():

    # Instance of VideoCapture to capture webcam(0) images
    # cap = cv2.VideoCapture(0)
    cap = cv2.VideoCapture('Videos/Video_003.avi')
    # cap = cv2.VideoCapture('sec_cam.mp4')

    # Getting width and height of captured images
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print "Width: ", w, "Height: ", h

    font = cv2.FONT_HERSHEY_SIMPLEX

    background_substractor = BackgroundSubtractor()
    blobs_detector = BlobDetector()
    tracker = Tracker()

    _time = time.time()

    number_frame = 0

    while True:
        ret, frame = cap.read()
        _fps = "%.2f" % (1 / (time.time() - _time))
        print (time.time() - _time)
        if float(_fps) > 24:
            # FIXME
            time.sleep(0.04)
        _time = time.time()

        to_show = background_substractor.apply(frame)
        blobs_points = blobs_detector.apply(to_show)

        number_frame += 1
        trayectos = tracker.apply(blobs_points, frame)

        to_show = cv2.drawKeypoints(to_show, blobs_points,
                                    outImage=np.array([]),
                                    color=(0, 0, 255),
                                    flags=
                                    cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

        cv2.putText(to_show, 'FPS: ' + _fps, (40, 40), font, 1,
                    (255, 255, 0), 2)

        for journey in [t.journey for t in trayectos if
                        t.last_update > datetime.now() - timedelta(seconds=1)]:
            for num in range(max(0, len(journey) - 20), len(journey) - 1):
                cv2.line(to_show, tuple(journey[num][0:2]),
                         tuple(journey[num+1][0:2]), (0, 155, 0), thickness=1)

        to_show = cv2.resize(to_show, (w*3, h*3))

        cv2.imshow('frame', to_show)
        cv2.imshow('frame2', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break




if __name__ == '__main__':

    do_the_thing()