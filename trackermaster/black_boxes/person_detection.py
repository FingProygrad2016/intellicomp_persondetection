import cv2
import numpy as np
from math import sqrt
from multiprocessing.pool import Pool

# from matplotlib import pyplot as plt
from imutils.object_detection import non_max_suppression

from utils.tools import crop_image_for_person_detection
from trackermaster.config import config
from trackermaster.black_boxes.histogram2d import Histogram2D

# Configuration parameters
ASPECT_RATIO = config.getfloat('ASPECT_RATIO')
PADDING = (config.getint('PADDING_0'), config.getint('PADDING_1'))
SCALE = config.getfloat('SCALE')
WIN_STRIDE = (config.getint('WINSTRIDE_0'),
              config.getint('WINSTRIDE_1'))


def apply_single(args):

    image, bounding_box, mult2, orig_f = args

    (rects, weights) = \
        HOG.detectMultiScale(image, winStride=WIN_STRIDE, padding=PADDING,
                             scale=SCALE)

    if len(rects):
        rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
        person = non_max_suppression(rects, probs=None, overlapThresh=0.65)
        del rects

        if len(person):
            return person, 1, bounding_box
    else:
        current_aspec_ratio = bounding_box[3] / bounding_box[2]
        if np.isclose(ASPECT_RATIO, current_aspec_ratio, atol=0.4):

            return [[bounding_box[0], bounding_box[1],
                     bounding_box[0] + bounding_box[2],
                     bounding_box[1]+bounding_box[3]]], \
                0.7 - (abs(ASPECT_RATIO - (bounding_box[2] / bounding_box[3]))),\
                bounding_box

    return [], 0, bounding_box


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
    global apply_single

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

        # TODO: Solucionar el mult2
        mult2 = 1

        # If there is not cropped image to process
        # (probably because the area is too small)
        if crop_img is None or mult2 == 0:
            continue

        # Draw in blue candidate blob
        cv2.rectangle(frame_resized_copy, (x, y), (x + w, y + h),
                      (255, 0, 0), 1)

        cropped_images.append((crop_img, (x, y, w, h), 1, 1))
    else:
        del rectangles

    if cropped_images:

        # if number_frame > 100:
        #     plt.scatter(HISTOGRAM_2D.widths, HISTOGRAM_2D.heights,
        #                 c=HISTOGRAM_2D.c)
        #     plt.show()

        res = PROCESSES_POOL.imap_unordered(apply_single, cropped_images)

        for xyAB in res:

            (x, y, w, h) = xyAB[2]
            score = xyAB[1]

            if number_frame <= 100:
                if score == 1:
                    HISTOGRAM_2D.create_confidence_matrix(xyAB[2])

            else:

                for person in xyAB[0]:
                    (xA, yA, xB, yB) = person

                    x_1 = int(round((xA * w) / 128))
                    y_1 = int(round((yA * h) / 256))
                    x_2 = int(round((xB * w) / 128))
                    y_2 = int(round((yB * h) / 256))

                    x_a = (x - 4) + x_1
                    x_b = (x + 4) + x_2
                    y_a = (y - 8) + y_1
                    y_b = (y + 8) + y_2

                    # Amarillo
                    color = 0 if score == 1 else 255
                    cv2.rectangle(frame_resized_copy, (x_a, y_a), (x_b, y_b),
                                  (0, color, 255), 2)

                    blobs.append(cv2.KeyPoint(round((x_a + x_b) / 2),
                                              round((y_a + y_b) / 2),
                                              sqrt(pow(x_b - x_a, 2) +
                                                   pow(y_b - y_a, 2))))
                    scores.append(score)

    return blobs, scores
