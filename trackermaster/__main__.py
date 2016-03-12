from __future__ import print_function
import inspect
import sys
import os
import json
import time
from hashlib import sha1
from imutils.object_detection import non_max_suppression
from math import pow, sqrt
from datetime import datetime as dt
import numpy as np
import cv2

from trackermaster.config import config, set_custome_config
from trackermaster.black_boxes.background_substraction import \
    BackgroundSubtractorKNN
from trackermaster.black_boxes.blob_detection import BlobDetector
from trackermaster.black_boxes.person_detection import PersonDetector
from trackermaster.black_boxes.tracking import Tracker
from utils.communicator import Communicator
from utils.tools import find_resolution_multiplier, \
    find_blobs_bounding_boxes, crop_image_for_person_detection, \
    frame2base64png

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)


def send_patternrecognition_config(communicator, identifier,
                                   patternmaster_conf):
    if patternmaster_conf:
        communicator.apply(json.dumps({'config': patternmaster_conf,
                                      'identifier': identifier}),
                           routing_key='processing_settings')


NUM_OF_POINTS = 40


def draw_journeys(journeys, outputs):
    """
    Draw lines in frame representing the path of each object

    :param journeys: list in which each item contains the path of an object
    :param outputs: list of outputs where to draw the lines

    :return: None
    """

    for journey in journeys:
        journey_data = journey[0]
        journey_color = journey[1]
        journey_id = journey[2]
        rectangle_points = journey[3]
        prediction = journey[4]
        has_big_blob = journey[5]

        if NUM_OF_POINTS > len(journey_data):
            num_of_points = len(journey_data)
        else:
            num_of_points = NUM_OF_POINTS
        num_of_points_2 = num_of_points/2

        # Draw the lines
        for i, (stretch_start, stretch_end) in \
                enumerate(zip(journey_data[-num_of_points:],
                              journey_data[-num_of_points+1:])):
            point_start = tuple(stretch_start[0:2])
            point_end = tuple(stretch_end[0:2])
            for output in outputs:
                cv2.line(output, point_start, point_end, journey_color,
                         thickness=2 if i > num_of_points_2 else 1)

        if has_big_blob:
            thickness = 2
        else:
            thickness = 1

        for output in outputs:
            cv2.rectangle(
                output, rectangle_points[0], rectangle_points[1], journey_color,
                thickness=thickness)
            cv2.circle(output, (prediction[0], prediction[1]), 3,
                       journey_color, -1)


def track_source(identifier=None, source=None, trackermaster_conf=None,
                 patternmaster_conf=None):

    if not identifier:
        identifier = sha1(str(dt.utcnow()).encode('utf-8')).hexdigest()
    if trackermaster_conf:
        set_custome_config(trackermaster_conf)

    # Instance of VideoCapture to capture webcam(0) images
    # WebCam
    # cap = cv2.VideoCapture(0)
    # popen("v4l2-ctl -d /dev/video1 --set-ctrl "
    #       "white_balance_temperature_auto=0,"
    #       "white_balance_temperature=inactive,exposure_absolute=inactive,"
    #       "focus_absolute=inactive,focus_auto=0,exposure_auto_priority=0")

    # Communication with Launcher and others
    comm_info = Communicator(exchange='to_master', exchange_type='topic')

    # Communication with PatternMaster
    communicator = \
        Communicator(exchange=config.get('TRACK_INFO_QUEUE_NAME'),
                     exchange_type='direct')
    exit_cause = 'FINISHED'

    send_patternrecognition_config(communicator, identifier, patternmaster_conf)

    if source:
        cap = cv2.VideoCapture(source)
        comm_info.send_message(
            json.dumps(dict(
                info_id="OPEN", id=identifier,
                content="Opening source: %s." % source)),
            routing_key='info')
    else:
        # Videos de muestra
        videos_path = os.path.dirname(
            os.path.abspath(inspect.getfile(inspect.currentframe())))
        source = videos_path + '/../Videos/Video_003.avi'
        cap = cv2.VideoCapture(source)

    has_at_least_one_frame, _ = cap.read()
    if not has_at_least_one_frame:
        comm_info.send_message(json.dumps(dict(
            info_id="EXIT WITH ERROR", id=identifier,
            content="<p>ERROR: Trying to open source but couldn't.</p>")),
            routing_key='info')
        print('EXIT %s with error: Source %s could not be loaded.' %
              (identifier, source))

        exit()

    # Original FPS
    try:
        FPS = float(int(cap.get(cv2.CAP_PROP_FPS)))
        if FPS == 0.:
            FPS = 24.
    except ValueError:
        FPS = 7.

    print("Working at", FPS, "FPS")
    SEC_PER_FRAME = 1. / FPS
    FPS_OVER_2 = (FPS / 2)

    # Getting width and height of captured images
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("Real resolution: Width", w, "Height", h)
    resolution_multiplier = find_resolution_multiplier(w, h)
    work_w = int(w / resolution_multiplier)
    work_h = int(h / resolution_multiplier)
    print("Work resolution: Width", work_w, "Height", work_h)

    font = cv2.FONT_HERSHEY_SIMPLEX

    background_subtractor = BackgroundSubtractorKNN()

    blobs_detector = BlobDetector()
    person_detector = PersonDetector()
    tracker = Tracker(SEC_PER_FRAME)

    loop_time = time.time()

    number_frame = 1
    _fps = "%.2f" % FPS
    previous_fps = FPS

    read_time = 0
    bg_sub_time = 0
    blob_det_time = 0
    t_time = 0
    pattern_recogn_time = 0
    show_info_time = 0
    display_time = 0
    wait_key_time = 0
    total_time = 0

    has_more_images = True

    # Start the main loop
    while has_more_images:

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
        has_more_images, frame = cap.read()

        number_frame += 1
        read_time += time.time() - t0

        if has_more_images:
            # resize to a manageable work resolution
            raw_frame = cv2.resize(frame, (work_w, work_h))
            frame = raw_frame.copy()
            frame_copy = frame.copy()
            frame_copy2 = frame.copy()

            # Black boxes process
            t0 = time.time()
            bg_sub = background_subtractor.apply(frame)
            to_show = bg_substraction = cv2.cvtColor(bg_sub, cv2.COLOR_GRAY2BGR)
            bg_sub_time += time.time() - t0
            t0 = time.time()
            blobs_points = blobs_detector.apply(bg_sub)

            if blobs_points:
                bounding_boxes = find_blobs_bounding_boxes(bg_sub)
                scores = []

                rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in
                                  bounding_boxes])
                rectangles = np.array([[x1, y1, x2 - x1, y2 - y1] for
                                       (x1, y1, x2, y2) in
                                       non_max_suppression(rects,
                                                           probs=None,
                                                           overlapThresh=0.3)])

                blobs = []
                for (x, y, w, h) in rectangles:
                    # Crop a rectangle around detected blob
                    crop_img = \
                        crop_image_for_person_detection(
                            frame_copy2, (x * resolution_multiplier,
                                          y * resolution_multiplier,
                                          w * resolution_multiplier,
                                          h * resolution_multiplier))

                    cv2.rectangle(frame_copy, (x, y), (x + w, y + h),
                                  (255, 0, 0), 2)
                    cv2.imshow('crop_img', crop_img)

                    persons, score = \
                        person_detector.apply((x, y, w, h), crop_img)

                    # draw the final bounding boxes
                    for (xA, yA, xB, yB) in persons:
                        x_1 = int(round((xA * w) / 128))
                        y_1 = int(round((yA * h) / 256))
                        x_2 = int(round((xB * w) / 128))
                        y_2 = int(round((yB * h) / 256))

                        x_a = (x - 4) + x_1
                        x_b = (x + 4) + x_2
                        y_a = (y - 8) + y_1
                        y_b = (y + 8) + y_2
                        cv2.rectangle(frame_copy, (x_a, y_a), (x_b, y_b),
                                      (0, 255, 0), 2)
                        blobs.append(cv2.KeyPoint(round((x_a + x_b) / 2),
                                                  round((y_a + y_b) / 2),
                                                  sqrt(pow(x_b - x_a, 2) +
                                                       pow(y_b - y_a, 2))))
                        scores.append(score)

                blob_det_time += time.time() - t0
                t0 = time.time()
                trayectos, info_to_send, tracklets = \
                    tracker.apply(blobs, frame, number_frame, scores)
                t_time += time.time() - t0

                t0 = time.time()

                if number_frame % FPS_OVER_2 == 0:
                    for info in info_to_send:
                        info['tracker_id'] = identifier
                        info['img'] = frame2base64png(raw_frame).decode()
                    # Send info to the pattern recognition every half second
                    communicator.apply(json.dumps(info_to_send),
                                       routing_key='track_info')

                if number_frame % (FPS*10) == 0:
                    # Renew the config in pattern recognition every 10 seconds
                    send_patternrecognition_config(communicator, identifier,
                                                   patternmaster_conf)

                # Draw circles in each blob
                to_show = \
                    cv2.drawKeypoints(
                        to_show, blobs_points,
                        outImage=np.array([]), color=(0, 0, 255),
                        flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

                # Write FPS in the frame to show
                cv2.putText(to_show, 'FPS: ' + _fps, (40, 40), font, 1,
                            (255, 255, 0), 2)

                pattern_recogn_time += time.time() - t0

                t0 = time.time()

                for tracklet in tracklets.values():
                    if getattr(tracklet, 'last_rule', None):
                        time_pass = dt.now() - \
                                    getattr(tracklet, 'last_rule_time')
                        if time_pass.seconds < 9:
                            cv2.putText(to_show, tracklet.last_rule,
                                        (int(tracklet.last_point[0]),
                                         int(tracklet.last_point[1])),
                                        font, 0.3 -
                                        (time_pass.seconds/30), (255, 0, 0), 1)
                        else:
                            tracklet.last_rule = None

                # Draw the journeys of the tracked persons
                draw_journeys(trayectos, [frame, to_show])

                show_info_time += time.time() - t0

                t0 = time.time()

            # Display the frames
            big_frame = np.vstack((np.hstack((bg_substraction, to_show)),
                                   np.hstack((frame, frame_copy))))
            big_frame = cv2.resize(big_frame, (work_w*4, work_h*4))
            cv2.imshow('result', big_frame)

            display_time += time.time() - t0

            t0 = time.time()

            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
                exit_cause = 'CLOSED'
                break

            wait_key_time += time.time() - t0

            total_time += time.time() - t_total

    cv2.destroyAllWindows()

    print("Average times::::")
    read_time = read_time / number_frame
    print("Read time " + str(read_time))
    bg_sub_time = bg_sub_time / number_frame
    print("Background subtraction time " + str(bg_sub_time))
    blob_det_time = blob_det_time / number_frame
    print("Blob detector time " + str(blob_det_time))
    t_time = t_time / number_frame
    print("Tracker time " + str(t_time))
    pattern_recogn_time = pattern_recogn_time / number_frame
    print("Communication with pattern recognition time " +
          str(pattern_recogn_time))
    show_info_time = show_info_time / number_frame
    print("Text and paths time " + str(show_info_time))
    display_time = display_time / number_frame
    print("Display time " + str(display_time))
    wait_key_time = wait_key_time / number_frame
    print("cv2.waitKey time " + str(wait_key_time))
    total_time = total_time / number_frame
    print("Total time " + str(total_time))

    comm_info = Communicator(exchange='to_master', exchange_type='topic')
    comm_info.send_message(json.dumps(dict(
        info_id="EXIT", id=identifier,
        content="Exit cause: " + exit_cause +
                "<br><img src='data:image/png;charset=utf-8;base64," +
                frame2base64png(raw_frame).decode() + "'>")),
        routing_key='info')

    exit()

if __name__ == '__main__':
    print('Start to process images...')
    track_source()
    print('END.')
