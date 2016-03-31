import cv2
import numpy as np
from math import sqrt
from multiprocessing.pool import Pool

from matplotlib import pyplot as plt
from imutils.object_detection import non_max_suppression

from trackermaster.config import config
from utils.tools import rect_size
from utils.tools import crop_image_for_person_detection


class PersonDetector:
    detector = None
    confidenceMatrix = None
    widths = []
    heights = []
    c = None

    def __init__(self):

        self.confidenceMatrix = np.zeros(shape=(32, 24), dtype=np.int32)

    def apply(self, bounding_box, image):
        (rects, weights) = \
            self.hog.detectMultiScale(image, winStride=self.winStride,
                                      padding=self.padding, scale=self.scale)
        # apply non-maxima suppression to the bounding boxes using a
        # fairly large overlap threshold to try to maintain overlapping
        # boxes that are still people
        rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
        person = non_max_suppression(rects, probs=None, overlapThresh=0.65)

        if len(person):
            max_person = max(person, key=rect_size)
            max_person_size = rect_size(max_person)

            min_person = min(person, key=rect_size)
            min_person_size = rect_size(min_person)

            return person, 1, min_person_size, max_person_size
        else:
            if (((bounding_box[2] / bounding_box[3]) >=
                (self.aspect_ratio - (0.2 * self.aspect_ratio))) and
                ((bounding_box[2] / bounding_box[3]) <=
                 (self.aspect_ratio + (0.2 * self.aspect_ratio)))):

                max_person = max([bounding_box], key=rect_size)
                max_person_size = rect_size(max_person)

                min_person = min([bounding_box], key=rect_size)
                min_person_size = rect_size(min_person)

                return [],\
                    0.7 - (abs(self.aspect_ratio - (bounding_box[2] /
                                                    bounding_box[3]))),\
                    min_person_size, max_person_size
            else:
                return [], 0, 0, 0

    def create_confidence_matrix(self, cropped_images):
        # TODO: Agregar arreglos x e y para mantener las medidas de las personas
        widths, heights = [], []
        xedges, yedges = np.linspace(0, 320, 32, endpoint=True),\
            np.linspace(0, 240, 24, endpoint=True)
        for cropped_image in cropped_images:
            (rects, weights) = \
                hog.detectMultiScale(cropped_image, winStride=winStride,
                                     padding=padding, scale=scale)
            # apply non-maxima suppression to the bounding boxes using a
            # fairly large overlap threshold to try to maintain overlapping
            # boxes that are still people
            rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
            persons = np.array([[x1, y1, x2 - x1, y2 - y1] for (x1, y1, x2, y2)
                                in non_max_suppression(rects, probs=None,
                                                       overlapThresh=0.65)])
            if len(persons):
                self.widths.append(cropped_image.shape[0])
                self.heights.append(cropped_image.shape[1])
        hist, xedges, yedges = np.histogram2d(self.widths, self.heights, (xedges, yedges))

        if self.confidenceMatrix.any():
            np.add(self.confidenceMatrix, hist, out=self.confidenceMatrix)
        else:
            self.confidenceMatrix = hist

        xidx = np.clip(np.digitize(widths, xedges), 0, hist.shape[0] - 1)
        yidx = np.clip(np.digitize(heights, yedges), 0, hist.shape[1] - 1)
        self.c = self.confidenceMatrix[xidx, yidx]
        # plt.scatter(widths, heights, c=c)
        #
        # plt.show()

        return self.confidenceMatrix

    def update_confidence(self, blob):
        return None

hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

# Configuration parameters
aspect_ratio = config.getfloat('ASPECT_RATIO')
padding = (config.getint('PADDING_0'), config.getint('PADDING_1'))
scale = config.getfloat('SCALE')
winStride = (config.getint('WINSTRIDE_0'),
             config.getint('WINSTRIDE_1'))

def apply_single(args):

    image, bounding_box, mult2, orig_f = args

    (rects, weights) = \
        hog.detectMultiScale(image, winStride=(4, 4), padding=(8, 8), scale=1.1)

    if len(rects):
        rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
        person = non_max_suppression(rects, probs=None, overlapThresh=0.65)
        del rects

        if len(person):
            max_person = max(person, key=rect_size)
            max_person_size = rect_size(max_person)

            min_person = min(person, key=rect_size)
            min_person_size = rect_size(min_person)

            return person, 1, min_person_size, max_person_size, bounding_box
            #return person, 1, mult2, orig_f
    else:
        current_aspec_ratio = bounding_box[3] / bounding_box[2]
        if np.isclose(aspect_ratio, current_aspec_ratio, atol=0.2):

            max_person = max([bounding_box], key=rect_size)
            max_person_size = rect_size(max_person)

            min_person = min([bounding_box], key=rect_size)
            min_person_size = rect_size(min_person)

            return [[bounding_box[0], bounding_box[1],
                     bounding_box[0] + bounding_box[2],
                     bounding_box[1]+bounding_box[3]]], \
                0.7 - (abs(aspect_ratio - (bounding_box[2] / bounding_box[3]))),\
                min_person_size, max_person_size, bounding_box
                # 0.7 - abs(aspect_ratio - current_aspec_ratio), mult2, orig_f
        else:
            return [], 0, 0, 0, bounding_box

pool_person_detectors = Pool()

min_person_size = 1000000
max_person_size = 0

# TODO: solucionar el tema de este metodo
person_detector = PersonDetector()


def apply(rectangles, resolution_multiplier, raw_frame_copy,
          frame_resized_copy, number_frame):

    global min_person_size
    global max_person_size
    global pool_person_detectors
    global hog

    to_process = []
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

        cropped_images.append(
            (crop_img,
             (x, y, w, h), 1, 1))
    else:
        del rectangles

    if number_frame <= 100:
        person_detector.create_confidence_matrix([x[0] for x in
                                                  cropped_images])
    elif cropped_images:

        plt.scatter(person_detector.widths, person_detector.heights,
                    c=person_detector.c)
        plt.show()

        res = pool_person_detectors.imap_unordered(apply_single, cropped_images)

        for xyAB in res:
            score = xyAB[1]
            #mult2 = xyAB[2]
            #x_orig_f, y_orig_f, w_orig_f, h_orig_f = xyAB[3]

            min_size = xyAB[2]
            max_size = xyAB[3]
            (x, y, w, h) = xyAB[4]

            # TODO: recalcular media considerando los historicos
            # TODO: utilizar media ponderada
            # (http://www.mathsisfun.com/data/weighted-mean.html)
            # TODO: combinar con histogramas
            # (http://progpython.blogspot.com.uy/2011/09/
            # histogramas-con-python-matplotlib.html)
            # TODO: https://ernestocrespo13.wordpress.com/2015/01/
            # 11/generacion-de-un-histograma-de-frecuencia-con-
            # numpy-scipy-y-matplotlib/
            if min_size > 0:
                min_person_size =\
                    np.median([min_person_size, min_size])
            if max_size > 0:
                max_person_size =\
                    np.median([max_person_size, max_size])
            # print("Min, max:", (min_person_size, max_person_size))

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
        else:
            del res
            del to_process
    return blobs, scores
