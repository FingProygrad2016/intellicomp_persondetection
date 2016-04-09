import cv2

# from matplotlib import pyplot as plt
from trackermaster.config import config
from utils.tools import crop_image_for_person_detection, x1y1x2y2_to_x1y1wh, \
    x1y1wh_to_x1y1x2y2
from trackermaster.black_boxes.histogram2d import Histogram2D
from trackermaster.black_boxes.person_detection_task import apply_single

import matplotlib
matplotlib.use('template')
from matplotlib import pyplot as plt

# Histogram2D unique instance
HISTOGRAM_2D = None

# Pool of processes for process person detection in parallel
PERSON_DETECTION_PARALLEL_MODE = \
    config.getboolean("PERSON_DETECTION_PARALLEL_MODE")
if PERSON_DETECTION_PARALLEL_MODE:
    import multiprocessing as mp
    from multiprocessing.pool import Pool
    import logging
    mp.log_to_stderr(logging.DEBUG)
    PROCESSES_POOL = Pool()


def set_histogram_size(shape):
    global HISTOGRAM_2D

    HISTOGRAM_2D = Histogram2D(shape=shape)


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
        cv2.rectangle(frame_resized_copy, (x, y),
                      (x + w, y + h), (255, 0, 0), 1)

        cropped_images.append((crop_img, resolution_multiplier))

    if cropped_images:

        if PERSON_DETECTION_PARALLEL_MODE:
            res = PROCESSES_POOL.imap_unordered(apply_single, cropped_images)
        else:
            res = map(apply_single, cropped_images)

        for xyAB in res:
            score = xyAB[1]

            if number_frame <= 100:
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

                    blobs.append({
                        "position": cv2.KeyPoint(round((x_a + x_b) / 2),
                                                 round((y_a + y_b) / 2),
                                                 (x_b - x_a) * (y_b - y_a)),
                        "box": ((x_a, y_a), (x_b, y_b))
                    })
                    scores.append(score)

    return blobs, scores
