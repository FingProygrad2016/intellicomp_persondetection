from uuid import uuid4
from datetime import datetime, timedelta
import random

import numpy as np
import cv2

from utils.tools import get_avg_color, euclidean_distance
from trackermaster.black_boxes.blob_assignment import \
    HungarianAlgorithmBlobPosition


# Ejmplo simple de Kalman Filter
# https://github.com/Itseez/opencv/blob/master/samples/python2/kalman.py
# https://github.com/simondlevy/OpenCV-Python-Hacks/blob/master/kalman_mousetracker.py
# Metodo para reconocer a que blob hacemos referencia (por color y tamano):
# http://airccse.org/journal/sipij/papers/2211sipij01.pdf


class Tracker:

    k_filters = []
    threshold_color = 30
    threshold_size = 1
    threshold_distance = 30
    tracklets_short_id = 1

    def __init__(self):
        pass

    def apply(self, blobs, raw_image):
        """
        For every blob, detect the corresponded tracked object and update it
        with the new information
        :param blobs: List of new blobs detected
        :param raw_image: The raw image captured
        :return: A list of TrackInfo which journey is greater than 5
        """

        info_to_send = {}
        to_remove = []

        for kf in self.k_filters:
            kf.hasBeenAssigned = False

        # Apply hungarian algorith for blob position
        habp = HungarianAlgorithmBlobPosition(self.threshold_distance, blobs)
        best_filters_per_blob = habp.apply(self.k_filters)

        for i in range(0, len(blobs)):
            blob = blobs[i]

            # Busco el filtro correspondiente al blob
            average_color = get_avg_color(raw_image, blob.pt)
            size = blob.size

            if best_filters_per_blob and best_filters_per_blob[i][1] != -1:
                matched_position = best_filters_per_blob[i][1]

                # Actualizo el estimador
                self.k_filters[matched_position]. \
                    update_info(new_position=blob.pt,
                                color=get_avg_color(raw_image, blob.pt),
                                size=blob.size, blob=blob)
            else:
                # Si no hay filtro creado para este blob, entonces creo uno
                matched_position = \
                    self.add_new_tracking(blob.pt,
                                          get_avg_color(raw_image, blob.pt),
                                          blob.size, blob)

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
                    kf.update_time()
                kf.predict()
            # If TrackInfo is too old, remove it forever
            if kf.last_update < datetime.now() - timedelta(seconds=1.5):
                to_remove.append(kf)
            else:
                # if len(kf.journey) > 5:
                journeys.append((kf.journey, kf.journey_color, kf.short_id,
                                 kf.rectangle, kf.prediction))

        # Remove the old tracked objects
        for x in to_remove:
            self.k_filters.remove(x)

        return journeys, [kf.to_dict() for kf in info_to_send], {k.id: k for k in self.k_filters}

    def add_new_tracking(self, point, color, size, blob):
        """
        Add a new instance of KalmanFilter and the corresponding metadata
        to the control collection.

        :param size:
        :param color:
        :return:
        """
        track_info = TrackInfo(color, size, point, self.tracklets_short_id, blob)
        self.k_filters.append(track_info)

        self.tracklets_short_id += 1

        return len(self.k_filters) - 1

    def search_nearest_blob(self, track_info, blobs):
        min_distance = 100000
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

    def __init__(self, color, size, point, short_id, blob):
        self.color = color
        self.size = size
        self.created_datetime = datetime.now()
        self.id = uuid4().hex
        self.short_id = short_id
        self.last_update = self.created_datetime
        self.last_point = point

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
                      [0, 0, 0, 0, 0, 1]],np.float32)
        self.kalman_filter.processNoiseCov = np.array([[1, 0, 0, 0, 0, 0],
                                                       [0, 1, 0, 0, 0, 0],
                                                       [0, 0, 1, 0, 0, 0],
                                                       [0, 0, 0, 1, 0, 0],
                                                       [0, 0, 0, 0, 1, 0],
                                                       [0, 0, 0, 0, 0, 1]],
                                                      np.float32) * 0.0001
        self.journey = []
        self.journey_color = (random.randint(0,255), random.randint(0,255), random.randint(0,255)) # (0, 155, 0)
        self.number_updates = 0

        arrayAux = np.array([[point[0]], [point[1]], [0.0], [0.0], [0.0], [0.0]], np.float32)
        self.kalman_filter.statePost = arrayAux

        self.hasBeenAssigned = True

        # prediction of next new position
        self.predict()

        self.journey.append(np.array(arrayAux.copy()))

    def __repr__(self):
        return "<TrackInfo color: %s, size: %s, last seen: %s, created: %s>" %\
               (self.color, self.size, self.last_update, self.created_datetime)

    def predict(self):

        self.prediction = self.kalman_filter.predict()


    def correct(self, measurement):
        correction = self.kalman_filter.correct(measurement)

        self.journey.append(np.array(correction.copy()))

        return correction

    def update_time(self):
        self.last_update = datetime.now()

    def update_info(self, new_position, color, size, blob):
        # correction with the known new position
        self.correct(np.array(new_position, np.float32))
        self.predict()
        self.color = color
        self.size = size
        self.last_update = datetime.now()
        self.last_point = new_position

        xt = int(round(blob.pt[0] - (blob.size / 4)))
        yt = int(round(blob.pt[1] - (blob.size / 2)))
        xb = int(round(blob.pt[0] + (blob.size / 4)))
        yb = int(round(blob.pt[1] + (blob.size / 2)))

        self.rectangle = ((xt, yt), (xb, yb))

        self.hasBeenAssigned = True

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
