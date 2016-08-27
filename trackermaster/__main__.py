from threading import Thread, Lock, Condition

import inspect
import json
import numpy as np
import cv2
import os
import sys
import time
import argparse

from hashlib import sha1
from datetime import datetime as dt

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)

from trackermaster.black_boxes import person_detection
from trackermaster.config import config, set_custome_config
from trackermaster.black_boxes.background_substraction import \
    BackgroundSubtractorKNN, BackgroundSubtractorMOG2
from trackermaster.black_boxes.blob_detection import BlobDetector
from trackermaster.black_boxes.tracking import Tracker
from utils.communicator import Communicator
from utils.tools import \
    find_resolution_multiplier, frame2base64png, x1y1x2y2_to_x1y1wh


USE_HISTOGRAMS_FOR_PERSON_DETECTION = None
SHOW_PREDICTION_DOTS = None
SHOW_COMPARISONS_BY_COLOR = None
SHOW_VIDEO_OUTPUT = None
LIMIT_FPS = None
DEFAULT_FPS_LIMIT = None
CREATE_MODEL = None
USE_MODEL = None
SAVE_POSITIONS_TO_FILE = None


def send_patternrecognition_config(communicator, instance_identifier,
                                   patternmaster_conf, resolution_mult):
    communicator.apply(json.dumps({'config': patternmaster_conf,
                                   'resolution_multiplier': resolution_mult,
                                  'identifier': instance_identifier}),
                       routing_key='processing_settings')

# NOTE: al aumentar/disminuir lo siguiente, el "Text and paths time"
#   cambia proporcionalmente.
NUM_OF_POINTS = 30


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
        for (stretch_start, stretch_end) in \
                zip(journey_data[-num_of_points:],
                    journey_data[-num_of_points+1:]):
            point_start = (stretch_start[0], stretch_start[3])
            point_end = (stretch_end[0], stretch_end[3])
            for output in outputs:
                cv2.line(output, point_start, point_end, journey_color,
                         thickness=1)

        if SHOW_PREDICTION_DOTS:
            for output in outputs:
                cv2.circle(output, (prediction[0], prediction[3]), 3,
                           journey_color, -1)

cap = None
has_more_images = True
raw_image = None
delay = 0
SEC_PER_FRAME = 0
number_frame = 1
reader_lock = Lock()
reader_condition = Condition()
kill_reader = False
processed = True


def read_raw_input():
    global has_more_images
    global raw_image
    global SEC_PER_FRAME
    global number_frame
    global processed
    time_aux_ = time.time()

    # reader_condition.wait()

    while True:

        if LIMIT_FPS:
            delay_ = time.time() - time_aux_
            time.sleep(max(SEC_PER_FRAME - delay_, 0))

        has_more_images_aux, raw_image_aux = cap.read()
        if LIMIT_FPS:
            time_aux_ = time.time()
            reader_lock.acquire()
        else:
            reader_condition.acquire()

        if not processed:
            reader_condition.wait(2)

        has_more_images = has_more_images_aux
        if not has_more_images or kill_reader:
            if LIMIT_FPS:
                reader_lock.release()
            else:
                reader_condition.notify()
                reader_condition.release()
            break
        raw_image = raw_image_aux.copy()

        if LIMIT_FPS:
            reader_lock.release()
        else:
            processed = False
            reader_condition.notify()
            reader_condition.release()

        number_frame += 1

    return None


def get_status_info_comm():
    STATUS_INFO_EXCHANGE_HOSTADDRESS = \
        config.get('STATUS_INFO_EXCHANGE_HOSTADDRESS')
    STATUS_INFO_EXCHANGE_NAME = \
        config.get('STATUS_INFO_EXCHANGE_NAME')
    STATUS_INFO_EXPIRATION_TIME = \
        config.getint('STATUS_INFO_EXPIRATION_TIME')
    comm_info = Communicator(host_address=STATUS_INFO_EXCHANGE_HOSTADDRESS,
                             exchange=STATUS_INFO_EXCHANGE_NAME,
                             exchange_type='topic',
                             expiration_time=STATUS_INFO_EXPIRATION_TIME)

    return comm_info


def track_source(identifier=None, source=None, trackermaster_conf=None,
                 patternmaster_conf=None):
    """
    :param identifier:
    :param source:
    :param trackermaster_conf:
    :param patternmaster_conf:
    :return:
    """

    """  START SETTING CONSTANTS  """

    global USE_HISTOGRAMS_FOR_PERSON_DETECTION, SHOW_PREDICTION_DOTS, \
        SHOW_COMPARISONS_BY_COLOR, SHOW_VIDEO_OUTPUT, LIMIT_FPS, \
        DEFAULT_FPS_LIMIT, CREATE_MODEL, USE_MODEL, SAVE_POSITIONS_TO_FILE

    USE_HISTOGRAMS_FOR_PERSON_DETECTION = \
        config.getboolean("USE_HISTOGRAMS_FOR_PERSON_DETECTION")
    SHOW_PREDICTION_DOTS = config.getboolean("SHOW_PREDICTION_DOTS")
    SHOW_COMPARISONS_BY_COLOR = config.getboolean("SHOW_COMPARISONS_BY_COLOR")
    SHOW_VIDEO_OUTPUT = config.getboolean("SHOW_VIDEO_OUTPUT")
    LIMIT_FPS = config.getboolean("LIMIT_FPS")
    DEFAULT_FPS_LIMIT = config.getfloat("DEFAULT_FPS_LIMIT")
    if CREATE_MODEL is None:
        CREATE_MODEL = config.getboolean("CREATE_MODEL")
    if USE_MODEL is None:
        USE_MODEL = config.getboolean("USE_MODEL")
    SAVE_POSITIONS_TO_FILE = config.getboolean("SAVE_POSITIONS_TO_FILE")
    USE_BSUBTRACTOR_KNN = config.getboolean("USE_BSUBTRACTOR_KNN")

    """  FINISH SETTING CONSTANTS  """

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
    comm_info = get_status_info_comm()

    # Communication with PatternMaster
    communicator = \
        Communicator(exchange=config.get('TRACK_INFO_EXCHANGE_NAME'),
                     host_address=config.get(
                         'TRACK_INFO_EXCHANGE_HOSTADDRESS'),
                     expiration_time=config.getint(
                         'TRACK_INFO_EXPIRATION_TIME'),
                     exchange_type='direct')
    exit_cause = 'FINISHED'

    global cap
    global has_more_images
    global raw_image
    global processed
    global SEC_PER_FRAME

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

    has_at_least_one_frame, raw_image = cap.read()

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
            FPS = DEFAULT_FPS_LIMIT
    except ValueError:
        FPS = DEFAULT_FPS_LIMIT

    reader = Thread(target=read_raw_input, daemon=True)
    reader.start()

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

    send_patternrecognition_config(communicator, identifier,
                                   patternmaster_conf, resolution_multiplier)

    font = cv2.FONT_HERSHEY_SIMPLEX

    background_subtractor = BackgroundSubtractorKNN() if USE_BSUBTRACTOR_KNN \
        else BackgroundSubtractorMOG2()

    blobs_detector = BlobDetector()
    # person_detector = Histogram2D()
    person_detection.pd_init_constants()
    tracker = Tracker(FPS, resolution_multiplier)

    loop_time = time.time()

    global number_frame
    _fps = "%.2f" % FPS
    previous_fps = FPS

    read_time = 0
    max_read_time = 0
    bg_sub_time = 0
    max_bg_sub_time = 0
    blob_det_time = 0
    max_blob_det_time = 0
    person_detection_time = 0
    max_person_detection_time = 0
    t_time = 0
    max_t_time = 0
    pattern_recogn_time = 0
    max_pattern_recogn_time = 0
    show_info_time = 0
    max_show_info_time = 0
    display_time = 0
    max_display_time = 0
    wait_key_time = 0
    max_wait_key_time = 0
    total_time = 0
    max_total_time = 0

    persons_in_scene = "Frame number (one-based), Current persons detected, " \
                       "Current tracklets, " \
                       "Current tracklets/persons interpol. num\n\n"

    model_load = False, ""
    if USE_HISTOGRAMS_FOR_PERSON_DETECTION:
        person_detection.set_histogram_size(shape=(work_w, work_h))
        person_detection.set_create_model(CREATE_MODEL)
        model_load = person_detection.set_use_model(USE_MODEL)

    fps = 0
    comparisons_by_color_image = []
    positions_to_file = ''
    interpol_cant_persons_prev = 0
    trayectos = []
    tracklets = {}
    last_number_frame = number_frame
    p_matrix_history = ''

    if model_load[0]:
        # Start the main loop
        while has_more_images:

            t_total = time.time()

            # FPS calculation
            if number_frame > 10 and number_frame != last_number_frame:
                delay = (time.time() - loop_time)
                loop_time = time.time()
                # if LIMIT_FPS:
                #     if delay < SEC_PER_FRAME:
                #         time_aux = time.time()
                #         time.sleep(max(SEC_PER_FRAME - delay, 0))
                #         delay += time.time() - time_aux

                fps = (1. / delay) * 0.25 + previous_fps * 0.75
                previous_fps = fps
                _fps = "%.2f" % fps

            else:
                if LIMIT_FPS:
                    while has_more_images and \
                            number_frame == last_number_frame:
                        time.sleep(0.01)  # Sleep for avoid Busy waiting
                    if not has_more_images:
                        break
                    loop_time = time.time()

            t0 = time.time()

            aux_time = time.time() - t0
            if number_frame > 200:
                read_time += aux_time
                max_read_time = max(aux_time, max_read_time)

            if has_more_images:
                # ########################################################## #
                # ##               BLACK BOXES PROCESSES                  ## #
                # ########################################################## #

                # ########################## ##
                # ## BACKGROUND SUBTRACTOR # ##
                # ########################## ##

                t0 = time.time()

                # resize to a manageable work resolution
                if LIMIT_FPS:
                    reader_lock.acquire()
                else:
                    reader_condition.acquire()
                    if number_frame == last_number_frame and has_more_images:
                        reader_condition.wait(2)

                if not has_more_images:
                    if LIMIT_FPS:
                        reader_lock.release()
                    else:
                        reader_condition.notify()
                        reader_condition.release()
                    break
                else:
                    last_number_frame = number_frame
                    raw_frame_copy = raw_image.copy()
                if LIMIT_FPS:
                    reader_lock.release()
                else:
                    processed = True
                    reader_condition.notify()
                    reader_condition.release()

                frame_resized = cv2.resize(raw_frame_copy, (work_w, work_h))
                frame_resized_copy = frame_resized.copy()

                bg_sub = background_subtractor.apply(frame_resized)
                bg_subtraction = cv2.cvtColor(bg_sub, cv2.COLOR_GRAY2BGR)
                to_show = bg_subtraction.copy()

                bg_subtraction_resized =\
                    cv2.resize(bg_subtraction, (work_w, work_h))

                aux_time = time.time() - t0
                if number_frame > 200:
                    bg_sub_time += aux_time
                    max_bg_sub_time = max(aux_time, max_bg_sub_time)

                # ################### ##
                # ## BLOBS DETECTOR # ##
                # ################### ##

                t0 = time.time()

                bounding_boxes = blobs_detector.apply(bg_sub)

                aux_time = time.time() - t0
                if number_frame > 200:
                    blob_det_time += aux_time
                    max_blob_det_time = max(aux_time, max_blob_det_time)

                t0 = time.time()

                cant_personas = 0

                if len(bounding_boxes):
                    rectangles = x1y1x2y2_to_x1y1wh(bounding_boxes)
                    del bounding_boxes

                    for (x, y, w, h) in rectangles:
                        # Draw in blue candidate blobs
                        cv2.rectangle(frame_resized_copy, (x, y),
                                      (x + w, y + h), (255, 0, 0), 1)

                    if len(rectangles) > 100:
                        # Skip the cycle when it's full of small blobs
                        continue

                    # ##################### ##
                    # ## PERSONS DETECTOR # ##
                    # ##################### ##
                    persons = person_detection.apply(
                        rectangles, resolution_multiplier, raw_frame_copy,
                        frame_resized_copy, number_frame, fps)
                    cant_personas = len(persons)

                    for p in persons:
                        # Red and Yellow dots
                        (x_a, y_a), (x_b, y_b) = p['box']
                        color = 0 if p['score'] == 1 else 255
                        cv2.circle(img=frame_resized_copy,
                                   center=(int((x_a + x_b) / 2),
                                           int((y_a + y_b) / 2)), radius=0,
                                   color=(0, color, 255), thickness=3)

                    aux_time = time.time() - t0
                    if number_frame > 200:
                        person_detection_time += aux_time
                        max_person_detection_time = \
                            max(aux_time, max_person_detection_time)

                    t0 = time.time()

                    # ############ ##
                    # ## TRACKER # ##
                    # ############ ##
                    rectangles_in_frame = []
                    trayectos_, info_to_send, tracklets, \
                        comparisons_by_color_image_aux, \
                        positions_in_frame,\
                        rectangles_in_frame,\
                        frame_p_matrix_history = \
                        tracker.apply(persons, frame_resized,
                                      bg_subtraction_resized, number_frame)
                    del persons
                    trayectos = trayectos_ if trayectos_ else trayectos

                    if SAVE_POSITIONS_TO_FILE:
                        if number_frame >= 50:
                            positions_to_file += positions_in_frame

                        for ((x1, y1), (x2, y2)) in rectangles_in_frame:
                            # Draw in green candidate blobs
                            cv2.rectangle(frame_resized_copy,
                                          (int(x1), int(y1)),
                                          (int(x2), int(y2)),
                                          (0, 255, 0), 1)

                        p_matrix_history += frame_p_matrix_history

                    if len(comparisons_by_color_image_aux) > 0:
                        comparisons_by_color_image = \
                            comparisons_by_color_image_aux

                    aux_time = time.time() - t0
                    if number_frame > 200:
                        t_time += aux_time
                        max_t_time = max(aux_time, max_t_time)

                    t0 = time.time()

                    # ################################################# ##
                    # ## COMMUNICATION WITH PATTERN MASTER AND OTHERS # ##
                    # ################################################# ##

                    if number_frame % FPS_OVER_2 == 0:
                        for info in info_to_send:
                            info['tracker_id'] = identifier

                            frame_resized_marks = frame_resized.copy()
                            cv2.rectangle(
                                frame_resized_marks, info['rectangle'][0],
                                info['rectangle'][1], (200, 0, 0), -1)
                            frame_resized_marks = \
                                cv2.addWeighted(frame_resized_marks, 0.2,
                                                frame_resized, 0.8, 0)
                            cv2.circle(frame_resized_marks,
                                       (int(info['last_position'][0]),
                                        int(info['last_position'][1])),
                                       70, (200, 200, 0), -1)
                            frame_resized_marks = \
                                cv2.addWeighted(frame_resized_marks, 0.2,
                                                frame_resized, 0.8, 0)
                            info['img'] = \
                                frame2base64png(frame_resized_marks).decode()
                        # Send info to the pattern recognition
                        # every half second
                        communicator.apply(json.dumps(info_to_send),
                                           routing_key='track_info')

                    if number_frame % (FPS*10) == 0:
                        # Renew the config in pattern recognition every
                        # 10 seconds
                        send_patternrecognition_config(
                            communicator, identifier, patternmaster_conf,
                            resolution_multiplier)

                    aux_time = time.time() - t0
                    if number_frame > 200:
                        pattern_recogn_time += aux_time
                        max_pattern_recogn_time = \
                            max(aux_time, max_pattern_recogn_time)

                t0 = time.time()

                now = dt.now()
                for tracklet in tracklets.values():
                    if getattr(tracklet, 'last_rule', None):
                        time_pass = now - getattr(tracklet, 'last_rule_time')
                        if time_pass.seconds < 9:
                            if SHOW_VIDEO_OUTPUT:
                                cv2.putText(
                                    to_show, tracklet.last_rule,
                                    (int(tracklet.last_point[0]),
                                     int(tracklet.last_point[1])),
                                    font, 0.3 - (time_pass.seconds/30),
                                    (255, 0, 0), 1)
                        else:
                            tracklet.last_rule = None

                if SHOW_VIDEO_OUTPUT:
                    # Draw the journeys of the tracked persons
                    draw_journeys(trayectos, [frame_resized_copy, to_show])

                aux_time = time.time() - t0
                if number_frame > 200:
                    show_info_time += aux_time
                    max_show_info_time = max(aux_time, max_show_info_time)

                if SAVE_POSITIONS_TO_FILE:
                    if number_frame >= 50:
                        persons_in_scene += str(number_frame) + ", " + \
                            str(cant_personas) + ", " + \
                            str(len(trayectos)) + ", " + str(round(
                                (len(trayectos) * .85) +
                                (cant_personas * .15))) + "\n"

                if SHOW_VIDEO_OUTPUT:
                    # #################### ##
                    # ## DISPLAY RESULTS # ##
                    # #################### ##

                    t0 = time.time()

                    big_frame = \
                        np.vstack((np.hstack((bg_subtraction, to_show)),
                                   np.hstack((frame_resized,
                                              frame_resized_copy))))
                    # TEXT INFORMATION
                    # Write FPS in the frame to show

                    cv2.putText(big_frame, 'Current persons detected: ' +
                                str(cant_personas), (20, 20), font, .5,
                                (255, 255, 0), 1)
                    cv2.putText(big_frame, 'Current tracklets: ' +
                                str(len(trayectos)), (20, 40), font, .5,
                                (255, 255, 0), 1)
                    interpol_cant_persons = round(
                        ((len(trayectos) * .7) + (cant_personas * .3)) * .35 +
                        interpol_cant_persons_prev * .65)
                    interpol_cant_persons_prev = interpol_cant_persons
                    cv2.putText(big_frame,
                                'Current tracklets/persons interpol. num: ' +
                                str(round((len(trayectos) * .85) +
                                          (cant_personas * .15))),
                                (20, 60), font, .5, (255, 255, 0), 1)
                    cv2.putText(big_frame, 'FPS: ' + _fps, (20, 80), font, .5,
                                (255, 255, 0), 1)

                    big_frame = cv2.resize(big_frame, (work_w*4, work_h*4))
                    cv2.imshow('result', big_frame)

                    if SHOW_COMPARISONS_BY_COLOR:
                        if len(comparisons_by_color_image) > 0:
                            cv2.imshow('comparisons by color',
                                       comparisons_by_color_image)

                    aux_time = time.time() - t0
                    if number_frame > 200:
                        display_time += aux_time
                        max_display_time = max(aux_time, max_display_time)

                    t0 = time.time()

                    if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
                        exit_cause = 'CLOSED BY PRESSING "Q|q"'
                        break

                    aux_time = time.time() - t0
                    if number_frame > 200:
                        wait_key_time += aux_time
                        max_wait_key_time = max(aux_time, max_wait_key_time)
                else:
                    print("frame: ", str(number_frame), "; fps: ", str(_fps))

                aux_time = time.time() - t_total
                if number_frame > 200:
                    total_time += aux_time
                    max_total_time = max(aux_time, max_total_time)

        global kill_reader
        kill_reader = True

        cv2.destroyAllWindows()

        if CREATE_MODEL:
            person_detection.save_histogram()

        number_frame_skip_first = number_frame - 200

        avg_times_text = "Average times::::"
        read_time /= number_frame_skip_first
        avg_times_text += "\nRead time " + str(read_time)
        bg_sub_time /= number_frame_skip_first
        avg_times_text += "\nBackground subtraction time " + str(bg_sub_time)
        blob_det_time /= number_frame_skip_first
        avg_times_text += "\nBlob detector time " + str(blob_det_time)
        person_detection_time /= number_frame_skip_first
        avg_times_text += "\nPerson detector time " + \
                          str(person_detection_time)
        t_time /= number_frame_skip_first
        avg_times_text += "\nTracker time " + str(t_time)
        pattern_recogn_time /= number_frame_skip_first
        avg_times_text += "\nCommunication with pattern recognition time " + \
                          str(pattern_recogn_time)
        show_info_time /= number_frame_skip_first
        avg_times_text += "\nText and paths time " + str(show_info_time)
        display_time /= number_frame_skip_first
        avg_times_text += "\nDisplay time " + str(display_time)
        wait_key_time /= number_frame_skip_first
        avg_times_text += "\ncv2.waitKey time " + str(wait_key_time)
        total_time /= number_frame_skip_first
        avg_times_text += "\nTotal time " + str(total_time)

        avg_times_text += "\n\n\nMax times::::"
        avg_times_text += "\nRead time " + str(max_read_time)
        avg_times_text += "\nBackground subtraction time " + \
                          str(max_bg_sub_time)
        avg_times_text += "\nBlob detector time " + str(max_blob_det_time)
        avg_times_text += "\nPerson detector time " + \
            str(max_person_detection_time)
        avg_times_text += "\nTracker time " + str(max_t_time)
        avg_times_text += "\nCommunication with pattern recognition time " + \
                          str(max_pattern_recogn_time)
        avg_times_text += "\nText and paths time " + str(max_show_info_time)
        avg_times_text += "\nDisplay time " + str(max_display_time)
        avg_times_text += "\ncv2.waitKey time " + str(max_wait_key_time)
        avg_times_text += "\nTotal time " + str(max_total_time)

        print(avg_times_text)

        if SAVE_POSITIONS_TO_FILE:
            with open("../experimental_analysis/raw_results/" + identifier +
                      "-positions.txt", "w") as text_file:
                print(positions_to_file, file=text_file)
            with open("../experimental_analysis/raw_results/" + identifier +
                      "-times.txt", "w") as text_file:
                print(avg_times_text, file=text_file)
            with open("../experimental_analysis/raw_results/" + identifier +
                      "-counter.txt", "w") as text_file:
                print(persons_in_scene, file=text_file)

            with open("../experimental_analysis/raw_results/" + identifier +
                      "-p_matrix.txt", "w") as text_file:
                print(p_matrix_history, file=text_file)

        comm_info = get_status_info_comm()
        comm_info.send_message(json.dumps(dict(
            info_id="EXIT", id=identifier,
            content="CAUSE: " + exit_cause,
            img=frame2base64png(frame_resized).decode())),
            routing_key='info')
    else:
        print(model_load[1])

    exit()

if __name__ == '__main__':
    print('Start to process images...')
    from sys import argv

    identifier = None
    source = None
    tmconf = None
    pmconf = None
    tmconffile_path = None
    train_model = None

    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--identifier", default=None,
                    help="identifier")
    ap.add_argument("-s", "--source", default=None,
                    help="path to source")
    ap.add_argument("-t", "--trackerconfjson", default=None,
                    help="tracker master .conf file in json format")
    ap.add_argument("-p", "--patternconfjson", default=None,
                    help="pattern master .conf file in json format")
    ap.add_argument("-f", "--trackerconffile", default=None,
                    help="tracker master .conf file path")
    ap.add_argument("-m", "--createmodel", default=None,
                    help="create model (Yes or No). By default it gets the "
                         "configuration from the .conf file")

    args = vars(ap.parse_args())

    identifier = args['identifier']
    source = args['source']
    if args['trackerconfjson']:
        tmconf = json.loads(args['trackerconfjson'])
    if args['patternconfjson']:
        pmconf = json.loads(args['patternconfjson'])
    if args['trackerconffile']:
        tmconffile_path = args['trackerconffile']

        if tmconffile_path[0:2] == './' or tmconffile_path[0:2] == '.\\':
            tmconffile_path = tmconffile_path[1:]
        elif tmconffile_path[0:3] == '../':
            tmconffile_path = '/' + tmconffile_path
        elif tmconffile_path[0:3] == '..\\':
            tmconffile_path = '\\' + tmconffile_path

        name_starts_in = 0
        if tmconffile_path.rfind('/') != -1:
            name_starts_in = tmconffile_path.rfind('/') + 1
        elif tmconffile_path.rfind('\\') != -1:
            name_starts_in = tmconffile_path.rfind('\\') + 1

        tmconffile_name = tmconffile_path[name_starts_in:]

        if not identifier:
            identifier = ""
        else:
            identifier += "-"
        identifier += tmconffile_name.replace('.conf', '')

        config.change_config_file(tmconffile_path)

    if args['createmodel']:
        if args['createmodel'] == "Yes":
            CREATE_MODEL = True
            USE_MODEL = False
        elif args['createmodel'] == "No":
            CREATE_MODEL = False

    if not (identifier or source or tmconf or pmconf):
        if len(argv) > 1:
            identifier = argv[1]
            source = argv[2]
            tmconf = json.loads(argv[3])
            pmconf = json.loads(argv[4])

    track_source(identifier=identifier, source=source,
                 trackermaster_conf=tmconf, patternmaster_conf=pmconf)

    print('END.')
