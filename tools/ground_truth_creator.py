import cv2
import numpy as np
import inspect
import os
import sys

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)

font = cv2.FONT_HERSHEY_SIMPLEX

global last_action_frame


def track_source(source=None):
    global last_action_frame

    def click_and_show(event, x, y, flags, param):
        global last_action_frame
        # if the left mouse button was clicked, record the
        # (x, y) coordinates and put the text on the image
        if event == cv2.EVENT_LBUTTONDOWN:
            last_action_frame = frame_resized.copy()
            cv2.putText(frame_resized, str(x) + ', ' + str(y),
                        (x, y), font, .5, (0, 0, 255), 1)
            # put the text on the image, with the coordinates
            cv2.imshow("image", frame_resized)
            print("x: ", str(x), ", y: ", str(y))

    if source:
        cap = cv2.VideoCapture(source)
    else:
        # Videos de muestra
        base_path = os.path.dirname(
            os.path.abspath(inspect.getfile(inspect.currentframe())))
        source_aux = base_path + '/../Videos/Video_003.avi'
        cap = cv2.VideoCapture(source_aux)

    # Original FPS
    try:
        FPS = float(int(cap.get(cv2.CAP_PROP_FPS)))
        if FPS == 0.:
            FPS = 7
    except ValueError:
        FPS = 7

    print("Working at", FPS, "FPS")

    # Getting width and height of captured images
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("Real resolution: Width", w, "Height", h)

    max_width = 320
    max_height = 240
    if w > max_width or h > max_height:
        mult_w = w / max_width
        mult_h = h / max_height
        if mult_w > mult_h:
            resolution_multiplier = mult_w
        else:
            resolution_multiplier = mult_h
    else:
        resolution_multiplier = 1

    work_w = int(w / resolution_multiplier)
    work_h = int(h / resolution_multiplier)
    print("Work resolution: Width", work_w, "Height", work_h)

    image_to_add_in_width = np.zeros((work_h, 120, 3), np.uint8)

    cv2.namedWindow("image")
    cv2.setMouseCallback("image", click_and_show)

    has_more_images, raw_image = cap.read()

    number_frame = 1

    exit_main_loop = False

    # Start the main loop
    while has_more_images and not exit_main_loop:

        if number_frame % FPS == 1:

            frame_resized = cv2.resize(raw_image, (work_w, work_h))
            aux_images = [frame_resized]
            aux_images.append(image_to_add_in_width)
            frame_resized = np.hstack(aux_images)

            print("frame: ", number_frame)
            cv2.putText(frame_resized, str(number_frame),
                        (5, 15), font, .5, (0, 0, 0), 1)

            clean_frame = frame_resized.copy()
            last_action_frame = frame_resized.copy()

            # #################### ##
            # ## DISPLAY RESULTS # ##
            # #################### ##
            keep_same_image = True

            while keep_same_image:
                cv2.imshow('image', frame_resized)

                key = cv2.waitKey(1) & 0xFF

                # if the 'n' key is pressed, go to next second
                if key == ord("n"):
                    keep_same_image = False
                elif key == ord("c"):
                    frame_resized = clean_frame.copy()
                elif key == ord("l"):
                    frame_resized = last_action_frame.copy()
                    print("last point was deleted")
                elif key == ord("q"):
                    keep_same_image = False
                    exit_main_loop = True

        has_more_images, raw_image = cap.read()
        number_frame += 1

    cv2.destroyAllWindows()

    exit()

if __name__ == '__main__':
    print('Start to process images...')
    from sys import argv
    source = None
    if len(argv) > 1:
        source = argv[1]
    track_source(source=source)
    print('END.')
