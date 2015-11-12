import cv2

from utils.tools import euclidean_distance
from trackermaster.config import config

__author__ = 'jp'

# Referencias en:
# http://www.learnopencv.com/blob-detection-using-opencv-python-c/


class BlobDetector:

    detector = None
    small_blobs_size_threshold = -1
    small_blobs_size_distance_threshold = -1
    small_blobs = []
    big_blobs = []

    # Configuration parameters
    threshold = [config.getint('MIN_THRESHOLD'), config.getint('MAX_THRESHOLD'), config.getint('THRESHOLD_STEP')]
    min_dist_between_blobs = config.getint('MIN_DIST_BETWEEN_BLOBS')
    filter_by_color = [config.getboolean('FILTER_BY_COLOR'), config.getint('BLOB_COLOR')]
    filter_by_area = [config.getboolean('FILTER_BY_AREA'), config.getint('MIN_AREA'), config.getint('MAX_AREA')]
    filter_by_circularity = [config.getboolean('FILTER_BY_CIRCULARITY'), config.getfloat('MIN_CIRCULARITY'),
                             config.getfloat('MAX_CIRCULARITY')]
    filter_by_convexity = [config.getboolean('FILTER_BY_CONVEXITY'), config.getfloat('MIN_CONVEXITY'),
                           config.getfloat('MAX_CONVEXITY')]
    filter_by_inertia = [config.getboolean('FILTER_BY_INERTIA'), config.getfloat('MIN_INERTIA'),
                         config.getfloat('MAX_INERTIA')]
    small_blobs_size_threshold = config.getint('SMALL_BLOBS_SIZE_THRESHOLD')
    small_blobs_size_distance_threshold = config.getint('SMALL_BLOBS_SIZE_DISTANCE_THRESHOLD')

    def __init__(self):

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
        self.small_blobs_size_threshold = self.small_blobs_size_threshold
        self.small_blobs_size_distance_threshold = self.small_blobs_size_distance_threshold

    # Try to identify small blobs with big blobs
    def identify_small_blobs(self):
        result = []
        small_blob_to_exclude = []

        for smallBlobIndex, smallBlob in enumerate(self.small_blobs):
            candidate = (None, 100000)
            for bigBlobIndex, bigBlob in enumerate(self.big_blobs):
                dist = euclidean_distance(smallBlob.pt, bigBlob.pt)
                if (dist < self.small_blobs_size_distance_threshold) and (dist < candidate[1]):
                    candidate = (bigBlobIndex, dist - (bigBlob.size / 2))
            if candidate[0]:
                # Calculo tamano total de la adicion del small blob
                # Uso max por el caso en que las areas se intersecten
                self.big_blobs[candidate[0]].size = \
                    max(self.big_blobs[candidate[0]].size,
                        self.big_blobs[candidate[0]].size + candidate[1])

                # Calculo punto medio ponderando por tamano de los blobs
                total_size = smallBlob.size + self.big_blobs[candidate[0]].size
                x_new = (self.big_blobs[candidate[0]].pt[0] *
                         self.big_blobs[candidate[0]].size +
                         smallBlob.pt[0] * smallBlob.size) / total_size
                y_new = (self.big_blobs[candidate[0]].pt[1] *
                         self.big_blobs[candidate[0]].size +
                         smallBlob.pt[1] * smallBlob.size) / total_size
                self.big_blobs[candidate[0]].pt = (x_new, y_new)
                small_blob_to_exclude.append(smallBlob)

        for blob in small_blob_to_exclude:
            self.small_blobs.remove(blob)

        # for smallBlob in self.small_blobs:
        #     result.append(smallBlob)

        for bigBlob in self.big_blobs:
            result.append(bigBlob)

        return result

    def apply(self, background):
        blobs = self.detector.detect(background)

        self.big_blobs = []
        self.small_blobs = []

        for blob in blobs:
            if blob.size > self.small_blobs_size_threshold:
                self.big_blobs.append(blob)
            else:
                self.small_blobs.append(blob)

        if self.small_blobs:
            result = self.identify_small_blobs()
            return result
        else:
            return self.big_blobs

        # return blobs
