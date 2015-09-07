import numpy as np
import cv2
import time
from black_boxes.background_substraction import BackgroundSubtractor
from black_boxes.blob_detection import BlobDetector
from black_boxes.tracking import Tracker


def do_the_thing():

    # Instance of VideoCapture to capture webcam(0) images
    # cap = cv2.VideoCapture(0)
    cap = cv2.VideoCapture('Videos/Video_003.avi')
    # cap = cv2.VideoCapture('sec_cam.mp4')

    # Getting width and height of captured images
    w = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
    print "Width: ", w, "Height: ", h

    font = cv2.FONT_HERSHEY_SIMPLEX

    background_substractor = BackgroundSubtractor()
    blobs_detector = BlobDetector()
    tracker = Tracker()

    _time = time.time()

    while True:
        ret, frame = cap.read()

        to_show = background_substractor.apply(frame)
        blobs_points = blobs_detector.apply(to_show)
        print blobs_points
        if blobs_points:
            print blobs_points[0]
            print blobs_points[0].pt
            print blobs_points[0].size
            # print help(blobs_points[0])
        to_show = cv2.drawKeypoints(to_show, blobs_points,
                                    outImage=np.array([]),
                                    color=(0,0,255),
                                    flags=
                                    cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

        # for blob in blobs_points:
        #     print help(blob)
        #     (x, y, w, h) = cv2.boundingRect(blob)
        #     cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 4)

        time_aux = time.time()
        _fps = "%.2f" % (1 / (time_aux - _time))

        # if float(_fps) > 10:
        #     time.sleep(0.03)

        _time = time_aux

        cv2.putText(to_show, 'FPS: ' + _fps, (40, 40), font, 1,
                    (255, 255, 0), 2)

        to_show = cv2.resize(to_show, (w*3, h*3))
        # frame = cv2.resize(frame, (w*3, h*3))

        cv2.imshow('frame', to_show)
        cv2.imshow('frame2', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


if __name__ == '__main__':

    do_the_thing()