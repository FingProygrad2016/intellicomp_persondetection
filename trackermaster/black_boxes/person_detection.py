import cv2
import numpy as np
from math import sqrt
from multiprocessing.pool import Pool

from imutils.object_detection import non_max_suppression
from trackermaster.config import config
from utils.tools import rect_size
from utils.tools import crop_image_for_person_detection

# import matplotlib
# matplotlib.use('template')
# from matplotlib import pyplot as plt

class PersonDetector:
    detector = None
    confidenceMatrix = None
    widths = []
    heights = []
    c = None

    def __init__(self):

        # Configuration parameters
        self.aspect_ratio = config.getfloat('ASPECT_RATIO')
        self.padding = (config.getint('PADDING_0'), config.getint('PADDING_1'))
        self.scale = config.getfloat('SCALE')
        self.winStride = (config.getint('WINSTRIDE_0'),
                          config.getint('WINSTRIDE_1'))

        # Initialize the HOG descriptor/person detector
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
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
                self.hog.detectMultiScale(cropped_image,
                                          winStride=self.winStride,
                                          padding=self.padding,
                                          scale=self.scale)
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


def apply_single(args):
    bounding_box, image, mult2, orig_f = args

    (rects, weights) = \
        hog.detectMultiScale(image, winStride=(4, 4), padding=(8, 8), scale=1.1)

    if len(rects):
        rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
        person = non_max_suppression(rects, probs=None, overlapThresh=0.65)
        del rects

        if len(person):
            return person, 1, mult2, orig_f
    else:
        current_aspec_ratio = bounding_box[3] / bounding_box[2]
        if np.isclose(2.0, current_aspec_ratio, atol=0.5):
            return [[bounding_box[0], bounding_box[1],
                     bounding_box[0] + bounding_box[2],
                     bounding_box[1]+bounding_box[3]]], \
                0.7 - abs(2.0 - current_aspec_ratio), mult2, orig_f
        else:
            return [], 0, mult2, orig_f

pool_person_detectors = Pool()


def apply(rectangles, resolution_multiplier, raw_frame_copy,
          frame_resized_copy):

    to_process = []
    blobs = []
    scores = []

    for (x, y, w, h) in rectangles:

        # Translate from minimized work image to the original
        (x_orig, y_orig,
         w_orig, h_orig) = (x * resolution_multiplier,
                            y * resolution_multiplier,
                            w * resolution_multiplier,
                            h * resolution_multiplier)

        # Crop a rectangle around detected blob
        crop_img, x_orig_f, y_orig_f, w_orig_f, h_orig_f, mult2 = \
            crop_image_for_person_detection(
                raw_frame_copy, (x_orig, y_orig, w_orig, h_orig))

        # If there is not cropped image to process
        # (probably because the area is too small)
        if crop_img is None or mult2 == 0:
            continue

        # Draw in blue candidate blob
        cv2.rectangle(frame_resized_copy, (x, y), (x + w, y + h),
                      (255, 0, 0), 1)

        to_process.append(((x_orig, y_orig, w_orig, h_orig),
                           crop_img.copy(), mult2,
                           (x_orig_f, y_orig_f, w_orig_f, h_orig_f)))
    else:
        del rectangles

    if to_process:

        res = pool_person_detectors.imap_unordered(apply_single, to_process)

        # draw the final bounding boxes
        for xyAB in res:
            score = xyAB[1]
            mult2 = xyAB[2]
            x_orig_f, y_orig_f, w_orig_f, h_orig_f = xyAB[3]

            for person in xyAB[0]:
                (xA, yA, xB, yB) = person

                xA_p = \
                    int((x_orig_f + (xA/mult2))/resolution_multiplier)
                yA_p = \
                    int((y_orig_f + (yA/mult2))/resolution_multiplier)
                xB_p = \
                    int((x_orig_f + (xB/mult2))/resolution_multiplier)
                yB_p = \
                    int((y_orig_f + (yB/mult2))/resolution_multiplier)

                # Amarillo
                color = 0 if score == 1 else 255
                cv2.rectangle(frame_resized_copy, (xA_p, yA_p), (xB_p, yB_p),
                              (0, color, 255), 2)

                blobs.append(cv2.KeyPoint(round((xA_p + xB_p)/2),
                                          round((yA_p + yB_p)/2),
                                          sqrt(xB_p*xB_p + xA_p*xA_p)))
                scores.append(score)
        else:
            del res
            del to_process

    return blobs, scores
