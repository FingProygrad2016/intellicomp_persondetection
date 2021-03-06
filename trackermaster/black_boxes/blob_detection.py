import cv2

from trackermaster.config import config
from utils.tools import x1y1wh_to_x1y1x2y2
from imutils.object_detection import non_max_suppression

# Referencias en:
# http://www.learnopencv.com/blob-detection-using-opencv-python-c/


class BlobDetector:

    detector = None

    def __init__(self):

        # Configuration parameters

        self.expand_blobs = (config.getboolean('EXPAND_BLOBS'),
                             config.getfloat('EXPAND_BLOBS_RATIO'))

        self.detect_blobs_by_bounding_boxes = \
            config.getboolean('DETECT_BLOBS_BY_BOUNDING_BOXES')

        # If SimpleBlobDetector will be used, load the parameters
        if not self.detect_blobs_by_bounding_boxes:

            self.threshold = [config.getint('MIN_THRESHOLD'),
                              config.getint('MAX_THRESHOLD'),
                              config.getint('THRESHOLD_STEP')]
            self.min_dist_between_blobs = \
                config.getint('MIN_DIST_BETWEEN_BLOBS')
            self.filter_by_color = [config.getboolean('FILTER_BY_COLOR'),
                                    config.getint('BLOB_COLOR')]
            self.filter_by_area = [config.getboolean('FILTER_BY_AREA'),
                                   config.getint('MIN_AREA'),
                                   config.getint('MAX_AREA')]
            self.filter_by_circularity = \
                [config.getboolean('FILTER_BY_CIRCULARITY'),
                 config.getfloat('MIN_CIRCULARITY'),
                 config.getfloat('MAX_CIRCULARITY')]
            self.filter_by_convexity = [config.getboolean('FILTER_BY_CONVEXITY'),
                                        config.getfloat('MIN_CONVEXITY'),
                                        config.getfloat('MAX_CONVEXITY')]
            self.filter_by_inertia = [config.getboolean('FILTER_BY_INERTIA'),
                                      config.getfloat('MIN_INERTIA'),
                                      config.getfloat('MAX_INERTIA')]



            # Setup SimpleBlobDetector parameters
            params = cv2.SimpleBlobDetector_Params()

            # Change thresholds
            params.minThreshold = self.threshold[0]
            params.maxThreshold = self.threshold[1]
            params.thresholdStep = self.threshold[2]

            # Minimum distance between blobs
            params.minDistBetweenBlobs = self.min_dist_between_blobs

            # Filter by Color
            params.filterByColor = self.filter_by_color[0]
            params.blobColor = self.filter_by_color[1]

            # Filter by Area.
            params.filterByArea = self.filter_by_area[0]
            params.minArea = self.filter_by_area[1]
            params.maxArea = self.filter_by_area[2]

            # Filter by Circularity
            params.filterByCircularity = self.filter_by_circularity[0]
            params.minCircularity = self.filter_by_circularity[1]
            params.maxCircularity = self.filter_by_circularity[2]

            # Filter by Convexity
            params.filterByConvexity = self.filter_by_convexity[0]
            params.minConvexity = self.filter_by_convexity[1]
            params.maxConvexity = self.filter_by_convexity[2]

            # Filter by Inertia
            params.filterByInertia = self.filter_by_inertia[0]
            params.minInertiaRatio = self.filter_by_inertia[1]
            params.maxInertiaRatio = self.filter_by_inertia[2]

            self.detector = cv2.SimpleBlobDetector_create(params)

    @staticmethod
    def find_blobs_bounding_boxes(bg_image, expand_blobs):
        """
        Find bounding boxes for each element of 'blobs'

        :param bg_image: the image containing the blobs
        :param expand_blobs:
        :return: a list of rectangles representing the bounding boxes

        """
        # Bounding boxes for each blob
        im2, contours, hierarchy = cv2.findContours(bg_image, cv2.RETR_TREE,
                                                    cv2.CHAIN_APPROX_SIMPLE)
        bounding_boxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if expand_blobs[0]:
                x = max(x - ((w * expand_blobs[1]) / 2), 0)
                y = max(y - ((h * expand_blobs[1]) / 2), 0)
                w = min(w * (expand_blobs[1] + 1), bg_image.shape[1])
                h = min(h * (expand_blobs[1] + 1), bg_image.shape[0])
            bounding_boxes.append((x, y, w, h))
        return bounding_boxes

    def apply(self, background):
        blobs = []

        if self.detect_blobs_by_bounding_boxes:
            blobs = self.find_blobs_bounding_boxes(
                background, self.expand_blobs)
        else:
            for keyPoint in self.detector.detect(background):
                if self.expand_blobs[0]:
                    x1 = max(keyPoint.pt[0] - keyPoint.size, 0)
                    y1 = max(keyPoint.pt[1] - keyPoint.size, 0)
                    x2 = min(keyPoint.pt[0] + keyPoint.size,
                             background.shape[1])
                    y2 = min(keyPoint.pt[1] + keyPoint.size,
                             background.shape[0])

                    w = x2 - x1
                    h = y2 - y1

                    x1 = max(x1 - ((w * self.expand_blobs[1]) / 2), 0)
                    y1 = max(y1 - ((h * self.expand_blobs[1]) / 2), 0)
                    x2 = min(x2 + ((w * self.expand_blobs[1]) / 2),
                             background.shape[1])
                    y2 = min(y2 + ((h * self.expand_blobs[1]) / 2),
                             background.shape[0])
                else:
                    x1 = max(keyPoint.pt[0] - keyPoint.size, 0)
                    y1 = max(keyPoint.pt[1] - keyPoint.size, 0)
                    x2 = min(keyPoint.pt[0] + keyPoint.size,
                             background.shape[1])
                    y2 = min(keyPoint.pt[1] + keyPoint.size,
                             background.shape[0])
                blobs.append((x1, y1, x2 - x1, y2 - y1))

        if blobs:
            blobs = non_max_suppression(x1y1wh_to_x1y1x2y2(blobs),
                                        overlapThresh=0.4)

        return blobs
