import json
import numpy as np
import cv2
import time
from datetime import datetime, timedelta
import pika

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
        FPS = 7.
    SEC_PER_FRAME = 1. / FPS
    FPS_OVER_2 = (FPS / 2)

    # Getting width and height of captured images
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print "Width: ", w, "Height: ", h

    font = cv2.FONT_HERSHEY_SIMPLEX

    # background_substractor = BackgroundSubtractorMOG2()
    background_substractor = BackgroundSubtractorKNN()
    blobs_detector = BlobDetector(100, 1000)
    tracker = Tracker()
    communicator = Communicator()

    # Warnings' receiver
    connection = pika.BlockingConnection()
    channel = connection.channel()
    new_warn = []

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
            trayectos, info_to_send, tracklets = tracker.apply(blobs_points, frame)

            if number_frame % FPS_OVER_2 == 0:
                # Send info to the pattern recognition every half second
                communicator.apply(info_to_send)

            # Draw circles in each blob
            #to_show = cv2.drawKeypoints(
            #    to_show, blobs_points, outImage=np.array([]), color=(0, 0, 255),
            #    flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

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
                        new_warn = json.loads(json.loads(warnings[2]))
                        print "NEW WARN", new_warn
                        rules = str(new_warn['rules'][0])
                        id_track = new_warn['id']
                        tracklet = tracklets.get(id_track, None)
                        if tracklet:
                            tracklet.last_rule = rules


            except pika.exceptions.ConnectionClosed:
                pass

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
                journey_id    = journey[2]
                rectangle_points = journey[3]
                for num in range(max(0, len(journey_data) - 30), len(journey_data) - 1):
                    cv2.line(to_show, tuple(journey_data[num][0:2]),
                             tuple(journey_data[num+1][0:2]), journey_color, thickness=1)
                    cv2.line(frame, tuple(journey_data[num][0:2]),
                             tuple(journey_data[num+1][0:2]), journey_color, thickness=1)
                cv2.rectangle(frame, rectangle_points[0], rectangle_points[1], journey_color)
                last_journey_point = (int(journey_data[len(journey_data) - 1][0][0]),
                                 int(journey_data[len(journey_data) - 1][1][0]))
                cv2.rectangle(frame, (last_journey_point[0], last_journey_point[1] - 7),
                              (last_journey_point[0] + 12, last_journey_point[1] + 1) , (255, 255, 255), -1)
                cv2.putText(frame, str(journey_id), last_journey_point, font, 0.3, journey_color, 1)

            # Draw rectangles for detected blobs
            #for blob in blobs_points:
            #    xt = int(round(blob.pt[0] - (blob.size / 4)))
            #    yt = int(round(blob.pt[1] - (blob.size / 2)))
            #    xb = int(round(blob.pt[0] + (blob.size / 4)))
            #    yb = int(round(blob.pt[1] + (blob.size / 2)))
            #    cv2.rectangle(frame, (xt, yt), (xb, yb), (0, 0, 255))

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
