import numpy as np
import cv2
import time


def do_the_thing():

    # Instance of VideoCapture to capture webcam(0) images
    # cap = cv2.VideoCapture(0)
    cap = cv2.VideoCapture('Videos/Video_003.avi')
    # cap = cv2.VideoCapture('sec_cam.mp4')

    # cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 640.0)
    # cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 480.0)

    # Getting width and height of captured images
    w = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
    print "Width: ", w, "Height: ", h

    # Threshold to consider a difference as a difference (u know what I mean)
    # _threshold = 300
    # print "Threshold: ", _threshold


    font = cv2.FONT_HERSHEY_SIMPLEX

    bg_sub_mog = cv2.BackgroundSubtractorMOG(nmixtures=2, backgroundRatio=0.1, history=500)

    # Setup SimpleBlobDetector parameters.
    params = cv2.SimpleBlobDetector_Params()

    # Change thresholds
    params.minThreshold = 5
    # params.thresholdStep = 5
    params.maxThreshold = 50

    # Filter by Area.
    params.filterByArea = True
    params.minArea = 55
    params.maxArea = 7000

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

    detector = cv2.SimpleBlobDetector(params)

    _time = time.time()
    _fps = ""

    ret, to_show = cap.read()
    while True:
        ret, frame = cap.read()

        to_show = frame
        to_show = cv2.cvtColor(to_show, cv2.cv.CV_BGR2GRAY)
        to_show = cv2.GaussianBlur(to_show, (11,11), 0)

        to_show = bg_sub_mog.apply(to_show, 0.3, 0.05)

        to_show = cv2.erode(to_show, np.ones((2,2),np.uint8), iterations=3)
        to_show = cv2.dilate(to_show, np.ones((4,1),np.uint8), iterations=1)
        to_show = cv2.dilate(to_show, np.ones((4,2),np.uint8), iterations=1)
        to_show = cv2.dilate(to_show, np.ones((2,3),np.uint8), iterations=1)
        # to_show = cv2.morphologyEx(src=to_show, op=cv2.MORPH_OPEN,
        #                            kernel=np.ones((3,3),np.uint8), iterations=1)
        # to_show = cv2.morphologyEx(src=to_show, op=cv2.MORPH_CLOSE,
        #                            kernel=np.ones((1,1),np.uint8), iterations=2)

        blobs_points = detector.detect(to_show)
        to_show = cv2.drawKeypoints(to_show, blobs_points, outImage=np.array([]), color=(0,0,255), flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

        # for blob in blobs_points:
        #     print help(blob)
        #     (x, y, w, h) = cv2.boundingRect(blob)
        #     cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 4)

        time_aux = time.time()
        _fps = "%.2f" % (1 / (time_aux - _time))

        # if float(_fps) > 10:
        #     time.sleep(0.03)

        _time = time_aux

        cv2.putText(to_show, 'FPS: ' + _fps, (40, 40), font, 1,
                    (255, 255, 0), 2)

        to_show = cv2.resize(to_show, (w*3, h*3))
        # frame = cv2.resize(frame, (w*3, h*3))

        cv2.imshow('frame', to_show)
        cv2.imshow('frame2', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


if __name__ == '__main__':
    do_the_thing()