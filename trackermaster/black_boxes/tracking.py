from uuid import uuid4
from datetime import datetime, timedelta
import random

import numpy as np
import cv2

from utils.tools import get_avg_color, euclidean_distance
from trackermaster.black_boxes.blob_assignment import \
    HungarianAlgorithm
from trackermaster.config import config

# Ejmplo simple de Kalman Filter
# https://github.com/Itseez/opencv/blob/master/samples/python2/kalman.py
# https://github.com/simondlevy/OpenCV-Python-Hacks/blob/master/kalman_mousetracker.py
# Metodo para reconocer a que blob hacemos referencia (por color y tamano):
# http://airccse.org/journal/sipij/papers/2211sipij01.pdf

INFINITE_DISTSTANCE = config.getint('INFINITE_DISTSTANCE')


class Tracker:

    k_filters = []
    threshold_color = config.getint('THRESHOLD_COLOR')
    threshold_size = config.getint('THRESHOLD_SIZE')
    threshold_distance = config.getint('THRESHOLD_DISTANCE')

    tracklets_short_id = 1

    def __init__(self, seconds_per_frame):
        self.last_frame = 0
        self.seconds_per_frame = seconds_per_frame

        # calculate the amount of valid frames to be without an update
        self.valid_frames_without_update = 1.5 / self.seconds_per_frame

        def position_distance_function(blob, k_filter):
            prediction = k_filter.kalman_filter.statePost
            return euclidean_distance((prediction[0], prediction[1]), blob.pt)

        # Hungarian Algorithm for blob position
        self.hung_alg_blob_pos = HungarianAlgorithm(position_distance_function, self.threshold_distance, INFINITE_DISTSTANCE)

        def blob_size_distance_function(blob, k_filter):
            return abs(blob.size - k_filter.size)

        # Hungarian Algorithm for blob size
        self.hung_alg_blob_size = HungarianAlgorithm(blob_size_distance_function, self.threshold_size, INFINITE_DISTSTANCE)

        def blob_color_distance_function(color, k_filter):
            return euclidean_distance(color, k_filter.color)

        # Hungarian Algorithm for blob color
        self.hung_alg_blob_color = HungarianAlgorithm(blob_color_distance_function, self.threshold_color, INFINITE_DISTSTANCE)

    def apply(self, blobs, raw_image, frame_number):
        """
        For every blob, detect the corresponded tracked object and update it
        with the new information
        :param blobs: List of new blobs detected
        :param raw_image: The raw image captured
        :return: A list of TrackInfo which journey is greater than 5
        """

        info_to_send = {}
        to_remove = []
        # elapsed_time = (frame_number - self.last_frame) * self.seconds_per_frame
        self.last_frame = frame_number

        for kf in self.k_filters:
            kf.hasBeenAssigned = False

        average_colors = []
        for blob in blobs:
            # Obtengo el color promedio del blob
            average_colors.append(get_avg_color(raw_image, blob.pt))

        # Apply hungarian algorithm for blob position
        best_filters_per_blob_pos = self.hung_alg_blob_pos.apply(blobs, self.k_filters)
        best_filters_per_blob_color = self.hung_alg_blob_color.apply(average_colors, self.k_filters)

        for i in range(0, len(blobs)):
            blob = blobs[i]

            size = blob.size

            if best_filters_per_blob_pos[i] != -1:
                matched_position = best_filters_per_blob_pos[i]

                # Actualizo el estimador
                self.k_filters[matched_position]. \
                    update_info(new_position=blob.pt,
                                color=average_colors[i],
                                size=blob.size, blob=blob, last_frame_update=frame_number)
            else:
                # Si no hay filtro creado para este blob, entonces creo uno
                matched_position = \
                    self.add_new_tracking(blob.pt,
                                          average_colors[i],
                                          blob.size, blob, frame_number)
                best_filters_per_blob_pos[i] = matched_position

            info_to_send[self.k_filters[matched_position].id] = \
                self.k_filters[matched_position]

        # Prepare the return data
        journeys = []
        info_to_send = info_to_send.values()
        for kf in self.k_filters: # number_trackinfo, track_info in enumerate(self.k_filters):
            # prediction of next new position
            if not kf.hasBeenAssigned:
                nearest_blob = self.search_nearest_blob(kf, blobs)
                if nearest_blob != -1:
                    kf.has_big_blob = True
                    self.k_filters[best_filters_per_blob_pos[nearest_blob]].has_big_blob = True
                    kf.update_last_frame(frame_number)
                else:
                    kf.has_big_blob = False
                kf.predict()
            # If TrackInfo is too old, remove it forever
            if self.last_frame - kf.last_frame_update > self.valid_frames_without_update:
                to_remove.append(kf)

        # Remove the old tracked objects
        for x in to_remove:
            self.k_filters.remove(x)

        for kf in self.k_filters:
            journeys.append((kf.journey, kf.journey_color, kf.short_id,
                             kf.rectangle, kf.prediction, kf.has_big_blob))

        return journeys, [kf.to_dict() for kf in info_to_send], {k.id: k for k in self.k_filters}

    def add_new_tracking(self, point, color, size, blob, frame_number):
        """
        Add a new instance of KalmanFilter and the corresponding metadata
        to the control collection.

        :param size:
        :param color:
        :return:
        """
        track_info = TrackInfo(color, size, point, self.tracklets_short_id, blob, frame_number)
        self.k_filters.append(track_info)

        self.tracklets_short_id += 1

        return len(self.k_filters) - 1

    def search_nearest_blob(self, track_info, blobs):
        min_distance = INFINITE_DISTSTANCE
        nearest_blob = -1
        for i in range(0, len(blobs)):
            prediction = track_info.kalman_filter.statePost
            distance = euclidean_distance((prediction[0], prediction[1]), blobs[i].pt)
            if distance < min_distance:
                min_distance = distance
                nearest_blob = i

        if min_distance <= self.threshold_distance:
            return nearest_blob
        else:
            return -1


class TrackInfo:

    def __init__(self, color, size, point, short_id, blob, frame_number):
        self.color = color
        self.size = size
        self.created_datetime = datetime.now()
        self.id = uuid4().hex
        self.short_id = short_id
        self.last_frame_update = frame_number
        self.last_update = self.created_datetime
        self.last_point = point
        self.has_big_blob = False

        xt = int(round(blob.pt[0] - (blob.size / 4)))
        yt = int(round(blob.pt[1] - (blob.size / 2)))
        xb = int(round(blob.pt[0] + (blob.size / 4)))
        yb = int(round(blob.pt[1] + (blob.size / 2)))

        self.rectangle = ((xt, yt), (xb, yb))
        self.kalman_filter = cv2.KalmanFilter(6, 2, 0)
        # self.kalman_filter.measurementMatrix = np.array([[1,0,0,0],
        #                                                  [0,1,0,0]],
        #                                                  np.float32)
        self.kalman_filter.measurementMatrix = \
            np.array([[1, 0, 1, 0, 0.5, 0], [0, 1, 0, 1, 0, 0.5]], np.float32)
        # self.kalman_filter.transitionMatrix = np.array([[1,0,1,0],
        #                                                 [0,1,0,1],
        #                                                 [0,0,1,0],
        #                                                 [0,0,0,1]],np.float32)
        self.kalman_filter.transitionMatrix = \
            np.array([[1, 0, 1, 0, 0.5, 0],
                      [0, 1, 0, 1, 0, 0.5],
                      [0, 0, 1, 0, 1, 0],
                      [0, 0, 0, 1, 0, 1],
                      [0, 0, 0, 0, 1, 0],
                      [0, 0, 0, 0, 0, 1]], np.float32)
        self.kalman_filter.processNoiseCov = np.array([[1, 0, 0, 0, 0, 0],
                                                       [0, 1, 0, 0, 0, 0],
                                                       [0, 0, 1, 0, 0, 0],
                                                       [0, 0, 0, 1, 0, 0],
                                                       [0, 0, 0, 0, 1, 0],
                                                       [0, 0, 0, 0, 0, 1]],
                                                      np.float32) * 0.0001
        self.journey = []
        self.journey_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.number_updates = 0

        array_aux = np.array([[point[0]], [point[1]], [0.0], [0.0], [0.0], [0.0]], np.float32)
        self.kalman_filter.statePost = array_aux

        self.hasBeenAssigned = True

        # prediction of next new position
        self.predict()

        self.journey.append(np.array(array_aux.copy()))

    def __repr__(self):
        return "<TrackInfo color: %s, size: %s, last seen: %s, created: %s>" %\
               (self.color, self.size, self.last_update, self.created_datetime)

    def predict(self):

        self.prediction = self.kalman_filter.predict()

    def correct(self, measurement):
        correction = self.kalman_filter.correct(measurement)

        self.journey.append(np.array(correction.copy()))

        return correction

    def update_last_frame(self, last_frame_update):
        self.last_frame_update = last_frame_update
        self.last_update = datetime.now()

    def update_info(self, new_position, color, size, blob, last_frame_update):
        # correction with the known new position
        self.correct(np.array(new_position, np.float32))
        self.predict()
        self.color = color
        self.size = size
        self.last_frame_update = last_frame_update
        self.last_update = datetime.now()
        self.last_point = new_position

        xt = int(round(blob.pt[0] - (blob.size / 4)))
        yt = int(round(blob.pt[1] - (blob.size / 2)))
        xb = int(round(blob.pt[0] + (blob.size / 4)))
        yb = int(round(blob.pt[1] + (blob.size / 2)))

        self.rectangle = ((xt, yt), (xb, yb))

        self.hasBeenAssigned = True
        self.has_big_blob = False

        self.number_updates += 1

    def to_dict(self):
        return {
            # "color": list(self.color),
            # "size": self.size,
            "created_timestamp":
                self.created_datetime.isoformat(),
            "id": self.id,
            "last_update_timestamp":
                self.last_update.isoformat(),
            "last_position": self.last_point
        }
