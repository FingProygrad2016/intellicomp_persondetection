import json
import numpy as np
import cv2
import time
from datetime import datetime, timedelta

from black_boxes.background_substraction import BackgroundSubtractorMOG2, \
    BackgroundSubtractorKNN
from black_boxes.blob_detection import BlobDetector
from black_boxes.communicator import Communicator
from black_boxes.tracking import Tracker


def start_to_process():

    # Instance of VideoCapture to capture webcam(0) images
    # cap = cv2.VideoCapture(0)
    cap = cv2.VideoCapture('Videos/Video_003.avi')
    # cap = cv2.VideoCapture('sec_cam.mp4')

    # Original FPS
    try:
        FPS = float(int(cap.get(cv2.CAP_PROP_FPS)))
    except ValueError:
        FPS = 24.
    SEC_PER_FRAME = 1. / FPS
    FPS_OVER_2 = (FPS / 2)

    # Getting width and height of captured images
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print "Width: ", w, "Height: ", h

    font = cv2.FONT_HERSHEY_SIMPLEX

    # background_substractor = BackgroundSubtractorMOG2()
    background_substractor = BackgroundSubtractorKNN()
    blobs_detector = BlobDetector()
    tracker = Tracker()
    communicator = Communicator()

    loop_time = time.time()

    number_frame = 1
    _fps = "%.2f" % FPS
    previous_fps = FPS

    hasMoreImages = True

    # Start the main loop
    while hasMoreImages:

        # FPS calculation
        if number_frame > 10:
            delay = (time.time() - loop_time)
            if delay < SEC_PER_FRAME:
                time_aux = time.time()
                time.sleep(max(SEC_PER_FRAME - delay, 0))
                delay += time.time() - time_aux
            fps = (1. / delay) * 0.25 + previous_fps * 0.75
            previous_fps = fps
            loop_time = time.time()
            _fps = "%.2f" % fps

        # Get a new frame
        hasMoreImages, frame = cap.read()
        number_frame += 1

        if hasMoreImages:
            # Black boxes process
            bg_sub = background_substractor.apply(frame)
            to_show = bg_sub
            blobs_points = blobs_detector.apply(bg_sub)
            trayectos, info_to_send = tracker.apply(blobs_points, frame)

            if number_frame % FPS_OVER_2 == 0:
                # Send info to the pattern recognition every half second
                communicator.apply(info_to_send)

            # Draw circles in each blob
            to_show = cv2.drawKeypoints(to_show, blobs_points,
                                        outImage=np.array([]),
                                        color=(0, 0, 255),
                                        flags=
                                        cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

            # Write FPS in the frame to show
            cv2.putText(to_show, 'FPS: ' + _fps, (40, 40), font, 1,
                        (255, 255, 0), 2)

            # Draw the journeys of the tracked persons
            # for journey in [t.journey for t in trayectos if
            #                 t.last_update > datetime.now() - timedelta(seconds=2)]:
            for journey in trayectos:
                for num in range(max(0, len(journey) - 30), len(journey) - 1):
                    cv2.line(to_show, tuple(journey[num][0:2]),
                             tuple(journey[num+1][0:2]), (0, 155, 0), thickness=1)
                    cv2.line(frame, tuple(journey[num][0:2]),
                             tuple(journey[num+1][0:2]), (0, 155, 0), thickness=1)

            # Resize the frames
            to_show = cv2.resize(to_show, (w*3, h*3))
            frame = cv2.resize(frame, (w*3, h*3))
            bg_sub = cv2.resize(bg_sub, (w*3, h*3))

            # Display the frames
            cv2.imshow('result', to_show)
            cv2.imshow('background subtraction', bg_sub)
            cv2.imshow('raw image', frame)

            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
                break


if __name__ == '__main__':
    print 'Start to process images...'
    start_to_process()
    print 'END.'
