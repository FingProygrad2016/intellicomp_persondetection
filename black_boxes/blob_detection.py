import cv2

__author__ = 'jp'

# Referencias en:
# http://www.learnopencv.com/blob-detection-using-opencv-python-c/


class BlobDetector:

    detector = None

    def __init__(self):
        # Setup SimpleBlobDetector parameters.
        params = cv2.SimpleBlobDetector_Params()

        # Change thresholds
        params.minThreshold = 5
        # params.thresholdStep = 5
        params.maxThreshold = 30

        # Filter by Area.
        params.filterByArea = True
        params.minArea = 50
        params.maxArea = 2100

        # Filter by Circularity
        params.filterByCircularity = False
        params.minCircularity = 0.01
        params.maxCircularity = 1.0

        # # Filter by Convexity
        params.filterByConvexity = False
        params.minConvexity = 0.01
        params.maxConvexity = 1.0

        # Filter by Inertia
        params.filterByInertia = False
        params.minInertiaRatio = 0
        params.maxInertiaRatio = 1

        params.minDistBetweenBlobs = 3

        params.filterByColor = True
        params.blobColor = 255

        self.detector = cv2.SimpleBlobDetector_create(params)

    def apply(self, background):
        return self.detector.detect(background)
