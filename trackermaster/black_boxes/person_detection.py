import cv2
import numpy as np

from imutils.object_detection import non_max_suppression
from trackermaster.config import config


class PersonDetector:

    detector = None

    # Configuration parameters
    aspect_ratio = config.getfloat('ASPECT_RATIO')
    padding = (config.getint('PADDING_0'), config.getint('PADDING_1'))
    scale = config.getfloat('SCALE')
    winStride = (config.getint('WINSTRIDE_0'), config.getint('WINSTRIDE_1'))

    def __init__(self):
        # Initialize the HOG descriptor/person detector
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

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
            return person, 1
        else:
            if (((bounding_box[2] / bounding_box[3]) >= (self.aspect_ratio - (0.25 * self.aspect_ratio))) and
                    ((bounding_box[2] / bounding_box[3]) <= (self.aspect_ratio + (0.25 * self.aspect_ratio)))):
                return [], 1 - (abs(self.aspect_ratio - (bounding_box[2] / bounding_box[3])))
            else:
                return [], 0
