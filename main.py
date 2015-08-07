import cv2
import time


def do_the_thing():

    # Instance of VideoCapture to capture webcam(0) images
    # cap = cv2.VideoCapture(0)
    cap = cv2.VideoCapture('/tmp/sec_cam.mp4')
    # cap.open()

    cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 640.0)
    cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 480.0)

    # Getting width and height of captured images
    w = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
    print "Width: ", w, "Height: ", h

    # print "FPS desde hardware: " + str(cap.get(cv2.cv.CV_CAP_PROP_FPS))

    # Threshold to consider a difference as a difference (u know what I mean)
    _threshold = 300
    print "Threshold: ", _threshold


    font = cv2.FONT_HERSHEY_SIMPLEX

    bg_sub_mog = cv2.BackgroundSubtractorMOG(nmixtures=2, backgroundRatio=0.5, history=1)

    # Setup SimpleBlobDetector parameters.
    params = cv2.SimpleBlobDetector_Params()
    # Change thresholds
    params.minThreshold = 10
    params.maxThreshold = 100
    # Filter by Area.
    params.filterByArea = True
    params.minArea = 20
    params.maxArea = 200
    # Filter by Circularity
    # params.filterByCircularity = True
    # params.minCircularity = 0.1
    # # Filter by Convexity
    # params.filterByConvexity = True
    # params.minConvexity = 0.1
    # Filter by Inertia
    params.filterByInertia = True
    params.minInertiaRatio = 0.01
    params.minDistBetweenBlobs = 1

    params.minArea = 20;
    params.minConvexity = 0.3;
    params.minInertiaRatio = 0.01;

    params.maxArea = 1000;
    params.maxConvexity = 10;

    detector = cv2.SimpleBlobDetector(params)

    _time = time.time()
    _fps = ""

    ret, to_show = cap.read()
    while True:
        ret, frame = cap.read()

        to_show = bg_sub_mog.apply(frame, 0.4, 0.05)

        blobs_points = detector.detect(to_show)
        to_show = cv2.drawKeypoints(to_show, blobs_points, color=(0,0,255), flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)


        time_aux = time.time()
        _fps = "%.2f" % (1 / (time_aux - _time))
        _time = time_aux

        cv2.putText(to_show, 'FPS: ' + _fps, (40, 40), font, 1,
                    (255, 255, 0), 2)

        cv2.imshow('frame', to_show)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


if __name__ == '__main__':
    do_the_thing()