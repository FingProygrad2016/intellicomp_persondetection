import numpy as np
import cv2

__author__ = 'jp'

# Ejmplo simple de Kalman Filter
# https://github.com/Itseez/opencv/blob/master/samples/python2/kalman.py
# https://github.com/simondlevy/OpenCV-Python-Hacks/blob/master/kalman_mousetracker.py
# Metodo para reconocer a que blob hacemos referencia (por color y tamano):
# http://airccse.org/journal/sipij/papers/2211sipij01.pdf


class Tracker:

    tracker = None
    initialized = False
    estimateds = []
    k_filters = []

    def __init__(self):
        self.tracker = cv2.KalmanFilter(4, 2, 0)

    def apply(self, position_blobs, raw_image):
        for position_blob in position_blobs:
            # Busco el filtro correspondiente al blob
            matched_filter = self.get_matched_kfilter(raw_image, position_blob)
            if matched_filter:
                # Actializo el estimador
                self.estimateds.append(matched_filter.predict())
                # TODO: El paramerto que se pasa en el corrector da error
                matched_filter.correct(position_blob.pt)
            else:
                # No hay filtro creado para este blob
                self.add_new_tracking(position_blob)

    def get_estimateds(self):
        return [k_filter.getEstimate() for k_filter in self.estimateds]

    def add_new_tracking(self, position_blob):
        k_filter = cv2.KalmanFilter(4, 2, 0)
        self.estimateds.append(k_filter.predict())
        # TODO: El paramerto que se pasa en el corrector da error
        k_filter.correct(position_blob.pt[0], position_blob.pt[1])
        self.k_filters.append(k_filter)

    def get_matched_kfilter(self, raw_image, position_blob):
        matched_filter = None
        center_color = \
            self.get_avg_color(raw_image,
                               position_blob.pt[0], position_blob.pt[1])
        size = position_blob.size

        for kfilter in self.k_filters:
            # Look for the best match
            # TODO: deberia guardar el average color y el tamano anterior!
            # Acordarse de hacer break de la iteracion al encontrar
            pass

        return matched_filter

    @staticmethod
    def get_avg_color(raw_image, x, y):
        # TODO: ESto deberia ir en un modulo de Tools generales...
        """
        Returns the average color in the square with center x and y.
        :param raw_image:
        :param x:
        :param y:
        :return:
        """
        # TODO
        return 255, 255, 255
