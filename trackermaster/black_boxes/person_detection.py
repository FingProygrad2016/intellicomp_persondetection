import cv2
import numpy as np

from imutils.object_detection import non_max_suppression
from trackermaster.config import config
from utils.tools import rect_size


class PersonDetector:
    detector = None
    confidenceMatrix = None

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
                widths.append(cropped_image.shape[0])
                heights.append(cropped_image.shape[1])
        hist, xedges, yedges = np.histogram2d(widths, heights, (xedges, yedges))
        # xidx = np.clip(np.digitize(widths, xedges), 0, hist.shape[0])
        # yidx = np.clip(np.digitize(heights, yedges), 0, hist.shape[1])
        # c = hist[xidx, yidx]
        #plt.scatter(widths, heights, c=c)

        #plt.show()

        if self.confidenceMatrix.any():
            np.add(self.confidenceMatrix, hist, out=self.confidenceMatrix)
        else:
            self.confidenceMatrix = hist

    def update_confidence(self, blob):
        return None
