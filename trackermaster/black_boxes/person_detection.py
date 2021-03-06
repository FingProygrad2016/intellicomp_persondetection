import cv2

import matplotlib
matplotlib.use('template')

from matplotlib import pyplot as plt
from trackermaster.config import config
from trackermaster.black_boxes.histogram2d import Histogram2D
from trackermaster.black_boxes.person_detection_task import apply_single, \
    pdt_init_constants
from utils.tools import crop_image_for_person_detection, normalize_matrix

# LOAD CONFIG. PARAMETERS
BORDER_AROUND_BLOB = None
USE_HISTOGRAMS_FOR_PERSON_DETECTION = None
FRAMES_COUNT_FOR_TRAINING_HISTOGRAMS = None
CONFIDENCE_MATRIX_UPDATE_TIME = None
PERSON_DETECTION_PARALLEL_MODE = None

# GLOBAL VARIABLES DECLARATION
last_update_frame = 0
update_confidence_matrix = False
# Histogram2D unique instance
HISTOGRAM_2D = None
CREATE_MODEL = None
USE_MODEL = None

PROCESSES_POOL = None


def pd_init_constants():
    global BORDER_AROUND_BLOB, USE_HISTOGRAMS_FOR_PERSON_DETECTION, \
        FRAMES_COUNT_FOR_TRAINING_HISTOGRAMS, CONFIDENCE_MATRIX_UPDATE_TIME, \
        PERSON_DETECTION_PARALLEL_MODE, PROCESSES_POOL

    # LOAD CONFIG. PARAMETERS
    BORDER_AROUND_BLOB = (config.getfloat("BORDER_AROUND_BLOB_0"),
                          config.getfloat("BORDER_AROUND_BLOB_1"))
    USE_HISTOGRAMS_FOR_PERSON_DETECTION = \
        config.getboolean("USE_HISTOGRAMS_FOR_PERSON_DETECTION")
    FRAMES_COUNT_FOR_TRAINING_HISTOGRAMS = \
        config.getint("FRAMES_COUNT_FOR_TRAINING_HISTOGRAMS")
    CONFIDENCE_MATRIX_UPDATE_TIME = \
        config.getint("CONFIDENCE_MATRIX_UPDATE_TIME")
    PERSON_DETECTION_PARALLEL_MODE = \
        config.getboolean("PERSON_DETECTION_PARALLEL_MODE")

    if PERSON_DETECTION_PARALLEL_MODE:
        from multiprocessing.pool import Pool
        PROCESSES_POOL = Pool()

    pdt_init_constants()


def set_histogram_size(shape):
    global HISTOGRAM_2D
    HISTOGRAM_2D = Histogram2D(shape=shape)


def set_create_model(create_model):
    global CREATE_MODEL
    CREATE_MODEL = create_model


def set_use_model(use_model):
    global USE_MODEL
    USE_MODEL = use_model

    result = True, ""
    if USE_MODEL:
        load = HISTOGRAM_2D.load()
        if load[0]:
            plt.imshow(HISTOGRAM_2D.normalizedConfidenceMatrix)
            plt.savefig('lala.png')
            plt.imshow(
                normalize_matrix(HISTOGRAM_2D.onePersonConfidenceMatrix))
            plt.savefig('lala2.png')
        else:
            result = False, load[1]
    return result


def crop_images(image, rect, resolution_multiplier):
    # Translate from minimized work image to the original
    (x_orig, y_orig, w_orig, h_orig) = (rect[0] * resolution_multiplier,
                                        rect[1] * resolution_multiplier,
                                        rect[2] * resolution_multiplier,
                                        rect[3] * resolution_multiplier)

    # Crop a rectangle around detected blob
    return crop_image_for_person_detection(image,
                                           (x_orig, y_orig, w_orig, h_orig),
                                           BORDER_AROUND_BLOB)


def must_update_histograms(number_frame, fps):
    global last_update_frame

    return (number_frame - last_update_frame) > \
           ((CONFIDENCE_MATRIX_UPDATE_TIME / 1000) * int(round(fps)))


def save_histogram():
    HISTOGRAM_2D.save()


def apply(rectangles, resolution_multiplier, raw_frame_copy,
          frame_resize_copy, number_frame, fps):

    global last_update_frame, update_confidence_matrix

    blobs = []
    cropped_images = []

    training_histograms = \
        CREATE_MODEL or ((not USE_MODEL) and
                         number_frame <= FRAMES_COUNT_FOR_TRAINING_HISTOGRAMS)

    update_confidence_matrix = (not (CREATE_MODEL or USE_MODEL)) and \
        USE_HISTOGRAMS_FOR_PERSON_DETECTION and (not training_histograms) and \
        (CONFIDENCE_MATRIX_UPDATE_TIME > 0) and \
        must_update_histograms(number_frame, fps)

    for (x, y, w, h) in rectangles:
        x_bin = min(int(round(w / 10.)),
                    int(frame_resize_copy.shape[1] / 10) - 1)
        y_bin = min(int(round(h / 10.)),
                    int(frame_resize_copy.shape[0] / 10) - 1)

        if USE_HISTOGRAMS_FOR_PERSON_DETECTION:
            if training_histograms or update_confidence_matrix:
                crop_img = crop_images(raw_frame_copy, (x, y, w, h),
                                       resolution_multiplier)

                # Add cropped image
                cropped_images.append((crop_img,
                                       resolution_multiplier, (w, h)))
            else:
                verify = HISTOGRAM_2D.verify_blob((x_bin, y_bin))
                if verify[0]:  # Need to check for persons
                    crop_img = crop_images(raw_frame_copy, (x, y, w, h),
                                           resolution_multiplier)

                    # Add cropped image
                    cropped_images.append((crop_img,
                                           resolution_multiplier, (w, h)))
                else:
                    if verify[1]:  # It's a person
                        blobs.append({
                            "position": cv2.KeyPoint(x + round(w / 2),
                                                     y + round(h / 2),
                                                     w * h),
                            "box": ((x, y), (x + w, y + h)),
                            "score": 1
                        })
        else:
            crop_img = crop_images(raw_frame_copy, (x, y, w, h),
                                   resolution_multiplier)

            # Add cropped image
            cropped_images.append((crop_img, resolution_multiplier, (w, h)))

    if cropped_images:
        if PERSON_DETECTION_PARALLEL_MODE:
            results_aux = []
            global PROCESSES_POOL
            results = \
                PROCESSES_POOL.imap_unordered(apply_single, cropped_images)
        else:
            results = list(map(apply_single, cropped_images))

        for persons_data in results:
            if PERSON_DETECTION_PARALLEL_MODE:
                results_aux.append(persons_data)

            score = persons_data[1]

            if USE_HISTOGRAMS_FOR_PERSON_DETECTION:
                if CREATE_MODEL or training_histograms:
                    if score == 1:
                        HISTOGRAM_2D.create_confidence_matrix(
                            (persons_data[2][0], persons_data[2][1],   # (X, Y
                             persons_data[3][0], persons_data[3][1]),  # ,W, H)
                            len(persons_data[0]))
                else:
                    for person in persons_data[0]:
                        x_a, y_a, x_b, y_b = person

                        blobs.append({
                            "position": cv2.KeyPoint(
                                round((x_a + x_b) / 2), round((y_a + y_b) / 2),
                                (x_b - x_a) * (y_b - y_a)),
                            "box": ((x_a, y_a), (x_b, y_b)),
                            "score": score
                        })
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
            if USE_HISTOGRAMS_FOR_PERSON_DETECTION and \
               (CREATE_MODEL or update_confidence_matrix):
                if PERSON_DETECTION_PARALLEL_MODE:
                    HISTOGRAM_2D.update_confidence_matrix(results_aux)
                    del results_aux
                else:
                    HISTOGRAM_2D.update_confidence_matrix(results)
                del results

                last_update_frame = number_frame
                update_confidence_matrix = False
                # plt.imshow(HISTOGRAM_2D.normalizedConfidenceMatrix)
                # plt.savefig('lala.png')
                # plt.imshow(
                #     normalize_matrix(HISTOGRAM_2D.onePersonConfidenceMatrix))
                # plt.savefig('lala2.png')
    if CREATE_MODEL:
        return []
    else:
        return blobs
