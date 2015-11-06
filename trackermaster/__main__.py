import sys
import os
path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)

import json
import time

import numpy as np
import cv2
import pika

from trackermaster.black_boxes.background_substraction import \
    BackgroundSubtractorKNN
from trackermaster.black_boxes.blob_detection import BlobDetector
from utils.communicator import Communicator
from trackermaster.black_boxes.tracking import Tracker


def start_to_process():

    # Instance of VideoCapture to capture webcam(0) images
    # cap = cv2.VideoCapture(0)
    # popen("v4l2-ctl -d /dev/video1 --set-ctrl white_balance_temperature_auto=0,"
    #       "white_balance_temperature=inactive,exposure_absolute=inactive,"
    #       "focus_absolute=inactive,focus_auto=0,exposure_auto_priority=0")
    cap = cv2.VideoCapture('../Videos/Video_003.avi')
    # cap = cv2.VideoCapture('sec_cam.mp4')

    # Original FPS
    try:
        FPS = float(int(cap.get(cv2.CAP_PROP_FPS)))
    except ValueError:
        FPS = 7.

    SEC_PER_FRAME = 1. / FPS
    FPS_OVER_2 = (FPS / 2)

    # Getting width and height of captured images
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print ("Width: ", w, "Height: ", h)

    size_mult_3 = (w*3, h*3)

    font = cv2.FONT_HERSHEY_SIMPLEX

    # background_substractor = BackgroundSubtractorMOG2()
    background_substractor = BackgroundSubtractorKNN()
    blobs_detector = BlobDetector(10, 10)
    tracker = Tracker(SEC_PER_FRAME)
    communicator = Communicator()

    # Warnings' receiver
    connection = pika.BlockingConnection()
    channel = connection.channel()
    new_warn = []

    loop_time = time.time()

    number_frame = 1
    _fps = "%.2f" % FPS
    previous_fps = FPS

    read_time = 0
    bs_time = 0
    bd_time = 0
    t_time = 0
    pr_time = 0
    tp_time = 0
    rs_time = 0
    wk_time = 0
    tt_time = 0

    hasMoreImages = True

    # Start the main loop
    while hasMoreImages:

        t_total = time.time()

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

        t0 = time.time()
        # Get a new frame
        hasMoreImages, frame = cap.read()
        number_frame += 1
        read_time += time.time() - t0

        if hasMoreImages:
            # Black boxes process
            t0 = time.time()
            bg_sub = background_substractor.apply(frame)
            to_show = bg_sub
            bs_time += time.time() - t0
            t0 = time.time()
            blobs_points = blobs_detector.apply(bg_sub)
            bd_time += time.time() - t0
            t0 = time.time()
            trayectos, info_to_send, tracklets = tracker.apply(blobs_points,
                                                               frame,
                                                               number_frame)
            t_time += time.time() - t0

            t0 = time.time()

            if number_frame % FPS_OVER_2 == 0:
                # Send info to the pattern recognition every half second
                communicator.apply(json.dumps(info_to_send))

            # Draw circles in each blob
            to_show = cv2.drawKeypoints(
               to_show, blobs_points, outImage=np.array([]), color=(0, 0, 255),
               flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

            # Write FPS in the frame to show
            cv2.putText(to_show, 'FPS: ' + _fps, (40, 40), font, 1,
                        (255, 255, 0), 2)

            try:
                while True:
                    connection = pika.BlockingConnection()
                    channel = connection.channel()
                    warnings = channel.basic_get('warnings')
                    if None in warnings:
                        break
                    else:
                        warnings = warnings[2].decode()
                        new_warn = json.loads(warnings)
                        print("NEW WARN", new_warn)
                        rules = str(new_warn['rules'][0])
                        id_track = new_warn['id']
                        tracklet = tracklets.get(id_track, None)
                        if tracklet:
                            tracklet.last_rule = rules

            except pika.exceptions.ConnectionClosed:
                pass

            pr_time += time.time() - t0

            t0 = time.time()

            for tracklet in tracklets.values():
                if getattr(tracklet, 'last_rule', None):
                    cv2.putText(to_show, tracklet.last_rule,
                                (int(tracklet.last_point[0]),
                                 int(tracklet.last_point[1])),
                                font, 0.3, (255, 0, 0), 1)

            # Draw the journeys of the tracked persons
            # for journey in [t.journey for t in trayectos if
            #                 t.last_update > datetime.now() - timedelta(seconds=2)]:
            for journey in trayectos:
                journey_data = journey[0]
                journey_color = journey[1]
                journey_id = journey[2]
                rectangle_points = journey[3]
                prediction = journey[4]

                journey_data_len = len(journey_data)

                for num in range(max(0, journey_data_len - 30), journey_data_len - 1):
                    tuple1 = tuple(journey_data[num][0:2])
                    tuple2 = tuple(journey_data[num+1][0:2])
                    cv2.line(to_show, tuple1, tuple2, journey_color, thickness=1)
                    cv2.line(frame, tuple1, tuple2, journey_color, thickness=1)
                cv2.rectangle(frame, rectangle_points[0], rectangle_points[1], journey_color, thickness=1)

                last_data = journey_data[journey_data_len - 1]
                last_journey_point = (int(last_data[0][0]), int(last_data[1][0]))
                cv2.rectangle(frame, (last_journey_point[0], last_journey_point[1] - 7),
                              (last_journey_point[0] + 12, last_journey_point[1] + 1) , (255, 255, 255), -1)
                cv2.putText(frame, str(journey_id), last_journey_point, font, 0.3, journey_color, 1)
                cv2.circle(frame, (prediction[0], prediction[1]), 3, journey_color, -1)

            tp_time += time.time() - t0

            t0 = time.time()
            # Resize the frames
            to_show = cv2.resize(to_show, size_mult_3)
            frame = cv2.resize(frame, size_mult_3)
            bg_sub = cv2.resize(bg_sub, size_mult_3)

            # Display the frames
            cv2.imshow('result', to_show)
            cv2.imshow('background subtraction', bg_sub)
            cv2.imshow('raw image', frame)

            rs_time += time.time() - t0

            t0 = time.time()

            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
                break

            wk_time += time.time() - t0

            tt_time += time.time() - t_total

    print("Average times::::")
    read_time = read_time / number_frame
    print("Read time " + str(read_time))
    bs_time = bs_time / number_frame
    print("Background subtraction time " + str(bs_time))
    bd_time = bd_time / number_frame
    print("Blob detector time " + str(bd_time))
    t_time = t_time / number_frame
    print("Tracker time " + str(t_time))
    pr_time = pr_time / number_frame
    print("Communication with pattern recognition time " + str(pr_time))
    tp_time = tp_time / number_frame
    print("Text and paths time " + str(tp_time))
    rs_time = rs_time / number_frame
    print("Image resize and show time " + str(rs_time))
    wk_time = wk_time / number_frame
    print("cv2.waitKey time " + str(wk_time))
    tt_time = tt_time / number_frame
    print("Total time " + str(tt_time))


if __name__ == '__main__':
    print('Start to process images...')
    start_to_process()
    print('END.')
