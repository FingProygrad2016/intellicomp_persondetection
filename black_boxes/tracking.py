import numpy as np
from uuid import uuid4
import cv2
from datetime import datetime, timedelta

from tools import get_avg_color, euclidean_distance

from blob_assignment import HungarianAlgorithmBlobPosition

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

        habp = HungarianAlgorithmBlobPosition(self.threshold_distance, blobs)
        costs = habp.apply(self.k_filters)

        for i in range(0, len(blobs)):
            blob = blobs[i]

            # Busco el filtro correspondiente al blob
            average_color = get_avg_color(raw_image, blob.pt)
            size = blob.size


            # matched_position = \
            #    self.get_matched_kfilter(blob.pt, average_color, size)

            if costs and costs[i][1] != -1:
                matched_position = costs[i][1]
            else:
                # Si no hay filtro creado para este blob, entonces creo uno
                matched_position = \
                    self.add_new_tracking(blob.pt,
                                          get_avg_color(raw_image, blob.pt),
                                          blob.size)

            # Actualizo el estimador
            self.k_filters[matched_position]. \
                update_info(new_position=blob.pt,
                            color=get_avg_color(raw_image, blob.pt),
                            size=blob.size)

            info_to_send[self.k_filters[matched_position].id] = \
                self.k_filters[matched_position]

        # Prepare the return data
        journeys = []
        info_to_send = info_to_send.values()
        for kf in self.k_filters:
            journeys.append(kf.journey)
            # prediction of next new position
            kf.predict()
            # info_to_send.append(kf.to_dict())


        for number_trackinfo, track_info in enumerate(self.k_filters):
            # If TrackInfo is too old, remove it forever
            if track_info.last_update < datetime.now() - timedelta(seconds=2):
                to_remove.append(track_info)
        # Remove the old tracked objects
        map(lambda x: self.k_filters.remove(x), to_remove)


        return journeys, [kf.to_dict() for kf in info_to_send]

    def add_new_tracking(self, point, color, size):
        """
        Add a new instance of KalmanFilter and the corresponding metadata
        to the control collection.

        :param size:
        :param color:
        :return:
        """
        track_info = TrackInfo(color, size, point)
        self.k_filters.append(track_info)

        return len(self.k_filters) - 1

    def get_matched_kfilter(self, blob_center, average_color, size):
        matched_filter = -1
        to_remove = []
        closest = []
        candidate = (-1, 1000000)
        for number_trackinfo, track_info in enumerate(self.k_filters):

            # If TrackInfo is too old, remove it forever
            if track_info.last_update < datetime.now() - timedelta(seconds=2):
                to_remove.append(track_info)
            else:
                # Look for the best match
                distance = euclidean_distance(blob_center, track_info.last_point)

                if distance < self.threshold_distance:
                    closest.append((number_trackinfo, track_info))
                    if candidate[1] > distance:
                        candidate = (number_trackinfo, distance)
                    # if abs(track_info.size - size) < self.threshold_size and \
                    # abs(track_info.color[0]-average_color[0]) < \
                    # self.threshold_color and \
                    # abs(track_info.color[1]-average_color[1]) < \
                    # self.threshold_color and \
                    # abs(track_info.color[2]-average_color[2]) < \
                    #     self.threshold_color:

        if closest.__len__() > 0:
            candidate2 = (-1, 1000000)
            for track_info_with_number in closest:
                previous = self.k_filters[track_info_with_number[0]].kalman_filter.statePre
                prediction = self.k_filters[track_info_with_number[0]].kalman_filter.statePost
                distance = euclidean_distance((prediction[0], prediction[1]), blob_center)
                if (distance < 1) & (candidate2[1] > distance):
                    candidate2 = (track_info_with_number[0], distance)
            if candidate2[0] != -1:
                number_trackinfo = candidate2[0]
            else:
                number_trackinfo = candidate[0]
            return number_trackinfo

        # Remove the old tracked objects
        map(lambda x: self.k_filters.remove(x), to_remove)

        return matched_filter


class TrackInfo:

    def __init__(self, color, size, point):
        self.color = color
        self.size = size
        self.created_datetime = datetime.now()
        self.id = uuid4().hex
        self.last_update = self.created_datetime
        self.last_point = point
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
        self.number_updates = 0

        arrayAux = np.array([[point[0]], [point[1]], [0.0], [0.0], [0.0], [0.0]], np.float32)
        self.kalman_filter.statePost = arrayAux

        # prediction of next new position
        self.predict()

        self.journey.append(np.array(arrayAux.copy()))

    def __repr__(self):
        return "<TrackInfo color: %s, size: %s, last seen: %s, created: %s>" %\
               (self.color, self.size, self.last_update, self.created_datetime)

    def predict(self):

        prediction = self.kalman_filter.predict()

    def correct(self, measurement):
        correction = self.kalman_filter.correct(measurement)

        self.journey.append(np.array(correction.copy()))

        return correction

    def update_info(self, new_position, color, size):
        # correction with the known new position
        self.correct(np.array(new_position, np.float32))
        self.color = color
        self.size = size
        self.last_update = datetime.now()
        self.last_point = new_position

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
