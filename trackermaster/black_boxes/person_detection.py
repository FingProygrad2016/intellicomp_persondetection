import cv2
import numpy as np
from math import sqrt
from multiprocessing.pool import Pool

# from matplotlib import pyplot as plt
from imutils.object_detection import non_max_suppression

from utils.tools import crop_image_for_person_detection, x1y1x2y2_to_x1y1wh, \
    x1y1wh_to_x1y1x2y2
from trackermaster.config import config
from trackermaster.black_boxes.histogram2d import Histogram2D

import matplotlib
matplotlib.use('template')
from matplotlib import pyplot as plt

# Configuration parameters
ASPECT_RATIO = config.getfloat('ASPECT_RATIO')
PADDING = (config.getint('PADDING_0'), config.getint('PADDING_1'))
SCALE = config.getfloat('SCALE')
WIN_STRIDE = (config.getint('WINSTRIDE_0'),
              config.getint('WINSTRIDE_1'))


def apply_single(args):

    image, bounding_box, mult2 = args[0]
    resolution_multiplier = args[1]

    persons = []
    score = 0

    (rects, weights) = HOG.detectMultiScale(
        image, winStride=WIN_STRIDE, padding=PADDING, scale=SCALE)

    if len(rects):
        persons = non_max_suppression(x1y1wh_to_x1y1x2y2(rects),
                                      overlapThresh=0.65)
        if len(persons):
            score = 1
    else:
        current_aspect_ratio = bounding_box[3] / bounding_box[2]
        if np.isclose(ASPECT_RATIO, current_aspect_ratio, atol=0.4):
            persons = [[0, 0, bounding_box[2], bounding_box[3]]]
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


# HOG unique instance
HOG = cv2.HOGDescriptor()
HOG.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

# Histogram2D unique instance
HISTOGRAM_2D = Histogram2D()

# Pool of processes for process person detection in parallel
PROCESSES_POOL = Pool()


def apply(rectangles, resolution_multiplier, raw_frame_copy,
          frame_resized_copy, number_frame):

    global PROCESSES_POOL

    blobs = []
    scores = []
    cropped_images = []

    for (x, y, w, h) in rectangles:

        # Translate from minimized work image to the original
        (x_orig, y_orig,
         w_orig, h_orig) = (x * resolution_multiplier,
                            y * resolution_multiplier,
                            w * resolution_multiplier,
                            h * resolution_multiplier)

        # Crop a rectangle around detected blob
        crop_img = \
            crop_image_for_person_detection(
                raw_frame_copy, (x_orig, y_orig, w_orig, h_orig))

        # Draw in blue candidate blob
        cv2.rectangle(frame_resized_copy, (x, y), (x + w, y + h),
                      (255, 0, 0), 1)

        cropped_images.append((crop_img, resolution_multiplier))

    if cropped_images:

        res = PROCESSES_POOL.imap_unordered(apply_single, cropped_images)

        for xyAB in res:

            # (x, y, w, h) = xyAB[2]
            score = xyAB[1]

            if number_frame <= 10:
                if score == 1:
                    HISTOGRAM_2D.create_confidence_matrix(xyAB[2])

            else:
                # plt.imshow(HISTOGRAM_2D.confidenceMatrix)
                # plt.savefig('lala.png')
                for person in xyAB[0]:

                    x_a, y_a, x_b, y_b = person

                    # Red and Yellow rectangles
                    color = 0 if score == 1 else 255
                    cv2.rectangle(frame_resized_copy, (x_a, y_a), (x_b, y_b),
                                  (0, color, 255), 2)

                    blobs.append(cv2.KeyPoint(round((x_a + x_b) / 2),
                                              round((y_a + y_b) / 2),
                                              sqrt(pow(x_b - x_a, 2) +
                                                   pow(y_b - y_a, 2))))
                    scores.append(score)

    return blobs, scores
