import cv2

from trackermaster.config import config
from utils.tools import crop_image_for_person_detection, verify_blob
from trackermaster.black_boxes.histogram2d import Histogram2D
from trackermaster.black_boxes.person_detection_task import apply_single

import matplotlib
matplotlib.use('template')
from matplotlib import pyplot as plt

# Histogram2D unique instance
HISTOGRAM_2D = None

BORDER_AROUND_BLOB = (config.getfloat("BORDER_AROUND_BLOB_0"),
                      config.getfloat("BORDER_AROUND_BLOB_1"))

CONFIDENCE_MATRIX_UPDATE_TIME = config.getint("CONFIDENCE_MATRIX_UPDATE_TIME")

last_update_frame = 0

# Pool of processes for process person detection in parallel
PERSON_DETECTION_PARALLEL_MODE = \
    config.getboolean("PERSON_DETECTION_PARALLEL_MODE")

if PERSON_DETECTION_PARALLEL_MODE:
    from multiprocessing.pool import Pool

    results_aux = []

    PROCESSES_POOL = Pool()


def set_histogram_size(shape):
    global HISTOGRAM_2D

    HISTOGRAM_2D = Histogram2D(shape=shape)


MIN_NUMBER_FRAMES_HISTOGRAM = 100


def apply(rectangles, resolution_multiplier, raw_frame_copy,
          frame_resized_copy, number_frame, fps):

    if PERSON_DETECTION_PARALLEL_MODE:
        global PROCESSES_POOL

    global last_update_frame, update_confidence_matrix

    blobs = []
    cropped_images = []
    confidence = []

    update_confidence_matrix = \
        (number_frame > MIN_NUMBER_FRAMES_HISTOGRAM) and \
        (CONFIDENCE_MATRIX_UPDATE_TIME > 0) and \
        ((number_frame - last_update_frame) >
         ((CONFIDENCE_MATRIX_UPDATE_TIME / 1000) * int(round(fps))))

    for (x, y, w, h) in rectangles:
        x_bin = int(round(w / float(10))) \
            if int(round(w / float(10))) < \
               int(frame_resized_copy.shape[1] / 10) \
            else int(round(w / float(10))) - 1
        y_bin = int(round(h / float(10))) \
            if int(round(h / float(10))) < \
               int(frame_resized_copy.shape[0] / 10) \
            else int(round(h / float(10))) - 1

        if (number_frame <= MIN_NUMBER_FRAMES_HISTOGRAM) or \
                update_confidence_matrix or \
                0 < HISTOGRAM_2D.normalizedConfidenceMatrix[x_bin][y_bin] < 0.2:
                    # Translate from minimized work image to the original
                    (x_orig, y_orig,
                     w_orig, h_orig) = (x * resolution_multiplier,
                                        y * resolution_multiplier,
                                        w * resolution_multiplier,
                                        h * resolution_multiplier)

                    # Crop a rectangle around detected blob
                    crop_img = \
                        crop_image_for_person_detection(raw_frame_copy,
                                                        (x_orig, y_orig,
                                                         w_orig, h_orig),
                                                        BORDER_AROUND_BLOB)

                    cropped_images.append((crop_img, resolution_multiplier, (w, h)))
        else:
            if HISTOGRAM_2D.normalizedConfidenceMatrix[x_bin][y_bin] >= 0.2:
                blobs.append({
                    "position": cv2.KeyPoint(round((x + w) / 2),
                                             round((y + h) / 2),
                                             w * h),
                    "box": ((x, y), (x + w, y + h)),
                    "score": 1
                })

    if cropped_images:
        if PERSON_DETECTION_PARALLEL_MODE:
            results = PROCESSES_POOL.imap_unordered(apply_single, cropped_images)
        else:
            results = map(apply_single, cropped_images)

        try:
            for persons_data in results:
                if PERSON_DETECTION_PARALLEL_MODE:
                    results_aux.append(persons_data)

                score = persons_data[1]

                if number_frame <= MIN_NUMBER_FRAMES_HISTOGRAM and score == 1:
                    HISTOGRAM_2D.create_confidence_matrix(
                        (persons_data[2][0], persons_data[2][1],   # (X  , Y
                         persons_data[3][0], persons_data[3][1]),  # ,W  , H)
                        len(persons_data[0]))
                else:
                    for person in persons_data[0]:
                        x_a, y_a, x_b, y_b = person

                        blobs.append({
                            "position": cv2.KeyPoint(round((x_a + x_b) / 2),
                                                     round((y_a + y_b) / 2),
                                                     (x_b - x_a) * (y_b - y_a)),
                            "box": ((x_a, y_a), (x_b, y_b)),
                            "score": score
                        })
            else:
                if update_confidence_matrix:
                    if PERSON_DETECTION_PARALLEL_MODE:
                        results = results_aux
                    HISTOGRAM_2D.update_confidence_matrix(results)
                    last_update_frame = number_frame
                    update_confidence_matrix = False
                    # plt.imshow(HISTOGRAM_2D.confidenceMatrix)
                    # plt.savefig('lala.png')

        except Exception as e:
            print(e)

    return blobs
