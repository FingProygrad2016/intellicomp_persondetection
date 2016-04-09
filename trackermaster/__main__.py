from __future__ import print_function
import inspect
import sys
import os
import json
import time
from hashlib import sha1
from datetime import datetime as dt

import numpy as np
print(np)
import cv2
print(cv2)
from imutils.object_detection import non_max_suppression

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)

from trackermaster.black_boxes import person_detection
from trackermaster.config import config, set_custome_config
from trackermaster.black_boxes.background_substraction import \
    BackgroundSubtractorKNN
from trackermaster.black_boxes.blob_detection import BlobDetector
from trackermaster.black_boxes.person_detection import Histogram2D
from trackermaster.black_boxes.tracking import Tracker
from utils.communicator import Communicator
from utils.tools import find_resolution_multiplier, frame2base64png,\
    x1y1wh_to_x1y1x2y2, x1y1x2y2_to_x1y1wh


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
        # journey_id = journey[2]
        # rectangle_points = journey[3]
        prediction = journey[4]
        # has_big_blob = journey[5]

        if NUM_OF_POINTS > len(journey_data):
            num_of_points = len(journey_data)
        else:
            num_of_points = NUM_OF_POINTS
        # num_of_points_2 = num_of_points/2

        # Draw the lines
        for i, (stretch_start, stretch_end) in \
                enumerate(zip(journey_data[-num_of_points:],
                              journey_data[-num_of_points+1:])):
            point_start = (stretch_start[0], stretch_start[3])
            point_end = (stretch_end[0], stretch_end[3])
            for output in outputs:
                cv2.line(output, point_start, point_end, journey_color,
                         thickness=1)

        if config.getboolean("SHOW_PREDICTION_DOTS"):
            for output in outputs:
                cv2.circle(output, (prediction[0], prediction[3]), 3,
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
    # person_detector = Histogram2D()
    tracker = Tracker(SEC_PER_FRAME)

    loop_time = time.time()

    number_frame = 1
    _fps = "%.2f" % FPS
    previous_fps = FPS

    read_time = 0
    bg_sub_time = 0
    blob_det_time = 0
    person_detection_time = 0
    t_time = 0
    pattern_recogn_time = 0
    show_info_time = 0
    display_time = 0
    wait_key_time = 0
    total_time = 0

    has_more_images = True

    min_person_size = 1000000
    max_person_size = 0

    person_detection.set_histogram_size(shape=(int(work_w / 10),
                                               int(work_h / 10)))

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
        has_more_images, raw_frame = cap.read()

        number_frame += 1
        read_time += time.time() - t0

        if has_more_images:

            original = raw_frame.copy()
            cv2.imshow("Original", original)

            # resize to a manageable work resolution
            raw_frame_copy = raw_frame.copy()
            frame_resized = cv2.resize(raw_frame, (work_w, work_h))
            frame_resized_copy = frame_resized.copy()

            # ################################################################ #
            # ##                  BLACK BOXES PROCESSES                     ## #
            # ################################################################ #

            # ########################## ##
            # ## BACKGROUND SUBTRACTOR # ##
            # ########################## ##

            t0 = time.time()

            bg_sub = background_subtractor.apply(frame_resized)
            bg_subtraction = cv2.cvtColor(bg_sub, cv2.COLOR_GRAY2BGR)
            to_show = bg_subtraction.copy()

            bg_subtraction_resized =\
                cv2.resize(bg_subtraction, (work_w, work_h))

            bg_sub_time += time.time() - t0

            # ################### ##
            # ## BLOBS DETECTOR # ##
            # ################### ##

            t0 = time.time()

            # blobs_points = blobs_detector.apply(bg_sub)
            # bounding_boxes = find_blobs_bounding_boxes(bg_sub)
            bounding_boxes =\
                blobs_detector.apply(bg_sub, min_person_size, max_person_size)

            blob_det_time += time.time() - t0
            t0 = time.time()

            cant_personas = 0
            trayectos = []

            if bounding_boxes:

                rectangles = x1y1x2y2_to_x1y1wh(
                    non_max_suppression(x1y1wh_to_x1y1x2y2(bounding_boxes),
                                        overlapThresh=0.3))

                # TODO: Remove!
                if len(rectangles) > 50:
                    # Skip the cycle when it's full of small blobs
                    print("TOO MUCH RECTANGLES!!!!")
                    continue

                # ##################### ##
                # ## PERSONS DETECTOR # ##
                # ##################### ##

                blobs, scores = \
                    person_detection.apply(rectangles, resolution_multiplier,
                                           raw_frame_copy, frame_resized_copy,
                                           number_frame)
                cant_personas = len(blobs)

                person_detection_time += time.time() - t0
                t0 = time.time()

                # ############ ##
                # ## TRACKER # ##
                # ############ ##

                trayectos, info_to_send, tracklets = \
                    tracker.apply(blobs, frame_resized, bg_subtraction_resized, number_frame, scores)
                del blobs
                del scores

                t_time += time.time() - t0
                t0 = time.time()

                # ################################################# ##
                # ## COMMUNICATION WITH PATTERN MASTER AND OTHERS # ##
                # ################################################# ##

                if number_frame % FPS_OVER_2 == 0:
                    for info in info_to_send:
                        info['tracker_id'] = identifier
                        info['img'] = frame2base64png(frame_resized).decode()
                    # Send info to the pattern recognition every half second
                    communicator.apply(json.dumps(info_to_send),
                                       routing_key='track_info')

                if number_frame % (FPS*10) == 0:
                    # Renew the config in pattern recognition every 10 seconds
                    send_patternrecognition_config(communicator, identifier,
                                                   patternmaster_conf)

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
                draw_journeys(trayectos, [frame_resized_copy, to_show])

                show_info_time += time.time() - t0

            # #################### ##
            # ## DISPLAY RESULTS # ##
            # #################### ##

            t0 = time.time()

            big_frame = np.vstack((np.hstack((bg_subtraction, to_show)),
                                   np.hstack((frame_resized, frame_resized_copy))))
            # TEXT INFORMATION
            # Write FPS in the frame to show

            cv2.putText(big_frame, 'Current persons detected: ' +
                        str(cant_personas), (20, 20), font, .5,
                        (255, 255, 0), 1)
            cv2.putText(big_frame, 'Current tracklets: ' +
                        str(len(trayectos)), (20, 40), font, .5,
                        (255, 255, 0), 1)
            cv2.putText(big_frame, 'Current tracklets/persons interpol. num: ' +
                        str(round((len(trayectos)*.85)+(cant_personas*.15))),
                        (20, 60), font, .5,
                        (255, 255, 0), 1)
            cv2.putText(big_frame, 'FPS: ' + _fps, (20, 80), font, .5,
                        (255, 255, 0), 1)

            big_frame = cv2.resize(big_frame, (work_w*4, work_h*4))
            cv2.imshow('result', big_frame)

            display_time += time.time() - t0

            t0 = time.time()

            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
                exit_cause = 'CLOSED BY PRESSING "Q|q"'
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
    person_detection_time = person_detection_time / number_frame
    print("Person detector time " + str(person_detection_time))
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
        content="CAUSE: " + exit_cause,
        img=frame2base64png(frame_resized).decode())),
        routing_key='info')

    exit()

if __name__ == '__main__':
    print('Start to process images...')
    track_source()
    print('END.')
