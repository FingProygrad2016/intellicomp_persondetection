import cv2

from utils.tools import euclidean_distance

__author__ = 'jp'

# Referencias en:
# http://www.learnopencv.com/blob-detection-using-opencv-python-c/


class BlobDetector:

    detector = None
    small_blobs_size_threshold = -1
    small_blobs_size_distance_threshold = -1
    small_blobs = []
    big_blobs = []

    def __init__(self, small_blobs_size_threshold,
                 small_blobs_size_distance_threshold):
        # Setup SimpleBlobDetector parameters.
        params = cv2.SimpleBlobDetector_Params()

        # Change thresholds
        params.minThreshold = 5
        # params.thresholdStep = 5
        params.maxThreshold = 30

        # Filter by Area.
        params.filterByArea = True
        params.minArea = 50
        params.maxArea = 5000

        # Filter by Circularity
        params.filterByCircularity = False
        params.minCircularity = 0.01
        params.maxCircularity = 1.0

        # Filter by Convexity
        params.filterByConvexity = False
        params.minConvexity = 0.2
        params.maxConvexity = 1.0

        # Filter by Inertia
        params.filterByInertia = False
        params.minInertiaRatio = 0
        params.maxInertiaRatio = 1

        params.minDistBetweenBlobs = 3

        params.filterByColor = True
        params.blobColor = 255

        self.detector = cv2.SimpleBlobDetector_create(params)
        self.small_blobs_size_threshold = small_blobs_size_threshold
        self.small_blobs_size_distance_threshold = \
            small_blobs_size_distance_threshold

    # Try to identify small blobs with big blobs
    def identify_small_blobs(self):
        result = []
        small_blob_to_exclude = []

        for smallBlobIndex, smallBlob in enumerate(self.small_blobs):
            candidate = (None, 100000)
            for bigBlobIndex, bigBlob in enumerate(self.big_blobs):
                dist = euclidean_distance(smallBlob.pt, bigBlob.pt)
                if (dist < self.small_blobs_size_distance_threshold) and \
                        (dist < candidate[1]):
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
