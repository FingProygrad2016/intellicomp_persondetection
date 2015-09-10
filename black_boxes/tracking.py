import numpy as np
from random import randint
from uuid import uuid4
import cv2
from datetime import datetime
from tools import get_avg_color

__author__ = 'jp'

# Ejmplo simple de Kalman Filter
# https://github.com/Itseez/opencv/blob/master/samples/python2/kalman.py
# https://github.com/simondlevy/OpenCV-Python-Hacks/blob/master/kalman_mousetracker.py
# Metodo para reconocer a que blob hacemos referencia (por color y tamano):
# http://airccse.org/journal/sipij/papers/2211sipij01.pdf


class Tracker:

    tracker = None
    initialized = False
    estimateds = {}
    k_filters = []
    threshold_color = 20
    threshold_size = 0.5

    def __init__(self):
        self.tracker = cv2.KalmanFilter(2, 2, 0)

    def apply(self, blobs, raw_image):
        for blob in blobs:
            # Busco el filtro correspondiente al blob
            average_color = get_avg_color(raw_image, blob.pt)
            size = blob.size
            matched_position = self.get_matched_kfilter(average_color, size)

            # Si no hay filtro creado para este blob
            if matched_position == -1:
                matched_position = self.add_new_tracking(
                    blob.size, get_avg_color(raw_image, blob.pt))

            # Actualizo el estimador
            self.k_filters[matched_position]. \
                update_info(new_point=blob.pt,
                            color=get_avg_color(raw_image, blob.pt),
                            size=blob.size)

            # Guardo la estimacion para retornarla
            info_id = self.k_filters[matched_position].id
            try:
                self.estimateds[info_id].\
                    append(self.k_filters[matched_position].predict())
            except KeyError:
                self.estimateds[info_id] = \
                    [self.k_filters[matched_position].predict()]

        print "Num kfilters:: ", len(self.k_filters)
        # print self.k_filters[0:10]
        # if randint(1,25) == 2:
        #     print self.k_filters
        # if randint(1,25) == 2:
        #     print self.estimateds

        return self.estimateds

    def add_new_tracking(self, size, color):
        """
        Add a new instance of KalmanFilter and the corresponding metadata
        to the control collection.

        :param size:
        :param color:
        :return:
        """
        track_info = TrackInfo(color, size)
        self.k_filters.append(track_info)

        return len(self.k_filters) - 1

    def get_matched_kfilter(self, average_color, size):
        matched_filter = -1
        for number_trackinfo, track_info in enumerate(self.k_filters):
            # Look for the best match
            if abs(track_info.size - size) < self.threshold_size and \
                abs(track_info.color[0]-average_color[0]) < \
                    self.threshold_color and \
                abs(track_info.color[1]-average_color[1]) < \
                    self.threshold_color and \
                abs(track_info.color[2]-average_color[2]) < \
                    self.threshold_color:
                print "MATCH! en ", number_trackinfo
                return number_trackinfo

        return matched_filter


class TrackInfo:

    def __init__(self, color, size):
        self.color = color
        self.size = size
        self.created_datetime = datetime.now()
        self.id = uuid4().hex
        self.last_update = self.created_datetime
        self.kalman_filter = cv2.KalmanFilter(2, 2, 0)

    def __repr__(self):
        return "<TrackInfo color: %s, size: %s, last seen: %s, created: %s>" %\
               (self.color, self.size, self.last_update, self.created_datetime)

    def predict(self, control=None):
        if control:
            return self.kalman_filter.predict(control)
        else:
            return self.kalman_filter.predict()

    def correct(self, measurement):
        return self.kalman_filter.correct(measurement)

    def update_info(self, new_point, color, size):
        self.correct(np.array(new_point, np.float32))
        self.color = color
        self.size = size
        self.last_update = datetime.now()
