import cv2
import numpy as np
from math import sqrt

from imutils.object_detection import non_max_suppression
from trackermaster.config import config

from utils.tools import x1y1wh_to_x1y1x2y2

# Configuration parameters
ASPECT_RATIO = config.getfloat('ASPECT_RATIO')
PADDING = (config.getint('PADDING_0'), config.getint('PADDING_1'))
SCALE = config.getfloat('SCALE')
WIN_STRIDE = (config.getint('WINSTRIDE_0'),
              config.getint('WINSTRIDE_1'))

first_time = True

def apply_single(args):

    image, bounding_box, mult2 = args[0]
    resolution_multiplier = args[1]

    persons = []
    score = 0

    global HOG
    global first_time

    # HOG unique instance
    if first_time:
        HOG = cv2.HOGDescriptor()
        aux = cv2.HOGDescriptor_getDefaultPeopleDetector()
        HOG.setSVMDetector(aux)
        first_time = False

    (rects, weights) = HOG.detectMultiScale(
        image, winStride=WIN_STRIDE, padding=PADDING, scale=SCALE)

    if len(rects):
        persons = non_max_suppression(x1y1wh_to_x1y1x2y2(rects),
                                      overlapThresh=0.65)
        if len(persons):
            score = 1
    else:
        current_aspect_ratio = image.shape[0] / image.shape[1]
        if np.isclose(ASPECT_RATIO, current_aspect_ratio, atol=0.5):
            persons = [[image.shape[1] * .125, image.shape[0] * .125,
                        image.shape[1] * .875, image.shape[0] * .875]]
            score = 0.7 - \
                (abs(ASPECT_RATIO - (bounding_box[2] / bounding_box[3])))

    (x, y, w, h) = bounding_box
    persons_resize = []
    for person in persons:

        (xA, yA, xB, yB) = person

        x_a = int(((x + (xA / mult2)) / resolution_multiplier))
        y_a = int(((y + (yA / mult2)) / resolution_multiplier))
        x_b = int(((x + (xB / mult2)) / resolution_multiplier))
        y_b = int(((y + (yB / mult2)) / resolution_multiplier))

        persons_resize.append((x_a, y_a, x_b, y_b))

    return persons_resize, score,\
           [(b / resolution_multiplier / mult2) for b in bounding_box]