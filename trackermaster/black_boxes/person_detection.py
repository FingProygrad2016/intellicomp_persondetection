import cv2
import numpy as np
from imutils.object_detection import non_max_suppression


class PersonDetector:

    detector = None

    def __init__(self):
        # Initialize the HOG descriptor/person detector
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self.winStride = (2, 2)
        self.padding = (4, 4)
        self.scale = 1.01

    def apply(self, image):
        (rects, weights) = self.hog.detectMultiScale(image, winStride=self.winStride, padding=self.padding,
                                                     scale=self.scale)
        # apply non-maxima suppression to the bounding boxes using a
        # fairly large overlap threshold to try to maintain overlapping
        # boxes that are still people
        rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
        return non_max_suppression(rects, probs=None, overlapThresh=0.65)
