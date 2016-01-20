from datetime import datetime
import inspect
import sys
import os
import numpy as np
import cv2
import json
import time
import pika
from hashlib import sha1
from datetime import datetime as dt
from trackermaster.config import config

from utils.tools import find_resolution_multiplier
from trackermaster.black_boxes.background_substraction import \
    BackgroundSubtractorKNN
from trackermaster.black_boxes.blob_detection import BlobDetector
from utils.communicator import Communicator
from trackermaster.black_boxes.tracking import Tracker

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)

# communicator = \
#     Communicator(queue_name=config.get('WARNINGS_QUEUE_NAME'),
#                  expiration_time=config.
#                  getint('WARNINGS_EXPIRATION_TIME'),
#                  host_address=config.get('WARNINGS_QUEUE_HOSTADDRESS'),
#                  exchange='to_master', exchange_type='topic')
#

def track_source(identifier=sha1(str(dt.utcnow()).encode('utf-8')).hexdigest(),
                 source=None):

    # Instance of VideoCapture to capture webcam(0) images

    # WebCam
    # cap = cv2.VideoCapture(0)
    # popen("v4l2-ctl -d /dev/video1 --set-ctrl "
    #       "white_balance_temperature_auto=0,"
    #       "white_balance_temperature=inactive,exposure_absolute=inactive,"
    #       "focus_absolute=inactive,focus_auto=0,exposure_auto_priority=0")
    if source:
        cap = cv2.VideoCapture(source)
    else:
        # Videos de muestra
        videos_path = os.path.dirname(
            os.path.abspath(inspect.getfile(inspect.currentframe())))
        cap = cv2.VideoCapture(videos_path + '/../Videos/Video_003.avi')
    # Palacio Legislativo
    # cap = cv2.VideoCapture('http://live.cdn.antel.net.uy/auth_0_byhzppsn,vxttoken=cGF0aFVSST0lMkZhdXRoXzBfYnloenBwc24lMkZobHMlMkYlMkEmZXhwaXJ5PTE0NDg5NTUzMzUmcmFuZG9tPW1qc2cwdnJHakYmYy1pcD0xOTAuNjQuNDkuMjcsMGI3OGU0NmQ5YjkyNTA0ZTZlYTY2ZDBlYTc1Yzk4OTI4YmZlOTczNmY4ZjQxM2QxMTc0MzYxNDBhOTBjOGRmZA==/hls/var1320000/playlist.m3u8')
    # Mercado del Puerto
    # cap = cv2.VideoCapture('http://live.cdn.antel.net.uy/auth_0_s2ujmpsk,vxttoken=cGF0aFVSST0lMkZhdXRoXzBfczJ1am1wc2slMkZobHMlMkYlMkEmZXhwaXJ5PTE0NDg5NTQ1OTkmcmFuZG9tPTZjaFFUTmk3MDMmYy1pcD0xOTAuNjQuNDkuMjcsM2IzNWZkNjQ4ODU5YTczZGVhNTA3OWVjZTFjMjNlMTFiOWQxMjJhZGIwNmRkYjFlNzIwNWY4ODYzNzU0ODU5MA==/hls/var3300000/playlist.m3u8')
    # Plaza del Entrevero
    # cap = cv2.VideoCapture('http://live.cdn.antel.net.uy/auth_0_3iwgu26m,vxttoken=cGF0aFVSST0lMkZhdXRoXzBfM2l3Z3UyNm0lMkZobHMlMkYlMkEmZXhwaXJ5PTE0NDg5NTU2MDcmcmFuZG9tPUFoNzJOVExHSXUmYy1pcD0xOTAuNjQuNDkuMjcsODI0NjhkZTM2NDNiMDQ5YjUyZmI3ZDNlNzUxY2M5NjRlOTMwMjFiM2UxNzUwMDRmZGI0ZWZhMWM4NTJlMjZlOQ==/hls/var3300000/playlist.m3u8')

    # cap = cv2.VideoCapture('sec_cam.mp4')

    # Original FPS
    try:
        FPS = float(int(cap.get(cv2.CAP_PROP_FPS)))
        if FPS == 0.:
            FPS = 24.
    except ValueError:
        FPS = 7.

    SEC_PER_FRAME = 1. / FPS
    FPS_OVER_2 = (FPS / 2)

    # Getting width and height of captured images
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("Real resolution: Width ", w, "Height ", h)
    resolution_multiplier = find_resolution_multiplier(w, h)
    work_w = int(w / resolution_multiplier)
    work_h = int(h / resolution_multiplier)
    print("Work resolution: Width ", work_w, "Height ", work_h)

    font = cv2.FONT_HERSHEY_SIMPLEX

    background_subtractor = BackgroundSubtractorKNN()

    blobs_detector = BlobDetector()
    tracker = Tracker(SEC_PER_FRAME)
    communicator = \
        Communicator(queue_name=config.get('TRACK_INFO_QUEUE_NAME'))

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
            frame = cv2.resize(frame, (work_w, work_h))

            # Black boxes process
            t0 = time.time()
            bg_sub = background_subtractor.apply(frame)
            to_show = np.copy(bg_sub)
            bg_sub_time += time.time() - t0
            t0 = time.time()
            blobs_points = blobs_detector.apply(bg_sub)

            # Bounding boxes for each blob
            im2, contours, hierarchy = cv2.findContours(bg_sub, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            bounding_boxes = []
            for contour in contours:
                bounding_boxes.append(cv2.boundingRect(contour))

            blob_det_time += time.time() - t0
            t0 = time.time()
            trayectos, info_to_send, tracklets = \
                tracker.apply(blobs_points, frame, number_frame)
            t_time += time.time() - t0

            t0 = time.time()

            if number_frame % FPS_OVER_2 == 0:
                for info in info_to_send:
                    info['tracker_id'] = identifier
                # Send info to the pattern recognition every half second
                communicator.apply(json.dumps(info_to_send))

            # Draw circles in each blob
            to_show = cv2.drawKeypoints(
               to_show, blobs_points, outImage=np.array([]), color=(0, 0, 255),
               flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

            # Write FPS in the frame to show
            cv2.putText(to_show, 'FPS: ' + _fps, (40, 40), font, 1,
                        (255, 255, 0), 2)

            # ### Warnings' receiver ###
            # try:
            #     while True:
            #         warnings = \
            #             communicator.channel.\
            #                 basic_get(config.get('WARNINGS_QUEUE_NAME'))
            #         if None in warnings:
            #             break
            #         else:
            #             warnings = warnings[2].decode()
            #             new_warn = json.loads(warnings)
            #             print("NEW WARN", new_warn)
            #             rules = str(new_warn['rules'][-1][1])
            #             id_track = new_warn['id']
            #             tracklet = tracklets.get(id_track, None)
            #             if tracklet:
            #                 tracklet.last_rule = rules
            #                 tracklet.last_rule_time = datetime.now()
            # except pika.exceptions.ConnectionClosed:
            #     pass
            # # END ### Warnings' receiver ###

            pattern_recogn_time += time.time() - t0

            t0 = time.time()

            for tracklet in tracklets.values():
                if getattr(tracklet, 'last_rule', None):
                    time_pass = datetime.now() - \
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
            for journey in trayectos:
                journey_data = journey[0]
                journey_color = journey[1]
                journey_id = journey[2]
                rectangle_points = journey[3]
                prediction = journey[4]
                has_big_blob = journey[5]

                journey_data_len = len(journey_data)

                for num in range(max(0, journey_data_len - 30),
                                 journey_data_len - 1):
                    tuple1 = tuple(journey_data[num][0:2])
                    tuple2 = tuple(journey_data[num+1][0:2])
                    cv2.line(to_show, tuple1, tuple2, journey_color,
                             thickness=1)
                    cv2.line(frame, tuple1, tuple2, journey_color, thickness=1)
                if has_big_blob:
                    thickness = 2
                else:
                    thickness = 1
                cv2.rectangle(frame, rectangle_points[0], rectangle_points[1],
                              journey_color, thickness=thickness)

                last_data = journey_data[journey_data_len - 1]
                last_journey_point = \
                    (int(last_data[0][0]), int(last_data[1][0]))
                cv2.rectangle(
                    frame, (last_journey_point[0], last_journey_point[1] - 7),
                    (last_journey_point[0] + 12, last_journey_point[1] + 1),
                    (255, 255, 255), -1
                )
                cv2.putText(frame, str(journey_id), last_journey_point, font,
                            0.3, journey_color, 1)
                cv2.circle(frame, (prediction[0], prediction[1]), 3,
                           journey_color, -1)

            # Draw bounding boxes
            for (x, y, w, h) in bounding_boxes:
                frame = cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)

            show_info_time += time.time() - t0

            t0 = time.time()

            # Display the frames
            # to_show = cv2.resize(to_show, (work_w*3, work_h*3))
            cv2.imshow('result', to_show)
            cv2.imshow('background subtraction', bg_sub)
            cv2.imshow('raw image', frame)

            display_time += time.time() - t0

            t0 = time.time()

            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
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

    exit()

if __name__ == '__main__':
    print('Start to process images...')
    track_source()
    print('END.')
