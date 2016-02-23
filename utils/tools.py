"""
Modulo que contiene funciones de ayuda generales
"""
import base64
import cv2
import numpy as np

MAX_WIDTH = 320
MAX_HEIGHT = 240


def get_avg_color(raw_image, point, square_half_width=2):
    """
    Returns the average color in the square with center x and y.
    :param raw_image:
    :param point: Tuple (x, y) with the center of the square
    :param square: width of the square where to take the average
    :return:
    """
    return raw_image[point[1]-square_half_width-1:point[1]+square_half_width,
                     point[1]-square_half_width-1:point[1]+square_half_width].\
        mean(axis=0).mean(axis=0)


def euclidean_distance(point1, point2):
    """
    Returns the euclidean distance between point 1 and 2.
    :param point1: Tuple with the position of the point 1
    :param point2: Tuple with the position of the point 2
    :return:
    """
    # FIXME: Ver si existe alternativa en Numpy (+ eficiente)
    return pow(abs(sum(map(lambda x_y: (x_y[0]-x_y[1])**2, zip(point1, point2)))
                   ), 0.5)


def diff_in_milliseconds(time_start, time_end):
    """
    Calculates the difference between two datetime with milliseconds precision
    :param datetime time_start:
    :param datetime time_end:
    :return: difference time_end - time_start in milliseconds
    :rtype: int
    """
    diff = time_end - time_start
    milliseconds = diff.days * 86400000  # 86400000 = 24 * 60 * 60 * 1000
    milliseconds += diff.seconds * 1000
    milliseconds += diff.microseconds / 1000  # microseconds to milliseconds

    return milliseconds


def find_resolution_multiplier(w, h):
    """
    Find a resolution divisor to get manageable resolution and then get the
    original back to show.
    :param w: real width
    :param h: real height
    :return: a float number
    """

    if w > MAX_WIDTH or h > MAX_HEIGHT:
        mult_w = w / MAX_WIDTH
        mult_h = h / MAX_HEIGHT
        if mult_w > mult_h:
            return mult_w
        else:
            return mult_h
    else:
        return 1


def find_blobs_bounding_boxes(bg_image):
    """
    Find bounding boxes for each element of 'blobs'
    :param bg_image: the image containing the blobs
    :return: a list of rectangles representing the bounding boxes
    """
    # Bounding boxes for each blob
    im2, contours, hierarchy = cv2.findContours(bg_image, cv2.RETR_TREE,
                                                cv2.CHAIN_APPROX_SIMPLE)
    bounding_boxes = []
    for contour in contours:
        bounding_boxes.append(cv2.boundingRect(contour))
    return bounding_boxes


def crop_image_for_person_detection(image, rect):
    """
    Crop an image generating a frame (border) around
    :param image: the original image
    :param rect: rectangle to crop
    :return: the image cropped with the frame (border) around
    """

    (x, y, w, h) = (rect[0], rect[1], rect[2], rect[3])

    if h >= (2 * w):
        w = h / 2
    else:
        h = 2 * w

    if (y - (h / 4)) > 0:
        y -= (h / 4)
    else:
        y = 0
    if (x - (w / 4)) > 0:
        x -= (w / 4)
    else:
        x = 0

    # NOTE: its img[y: y + h, x: x + w] and *not* img[x: x + w, y: y + h]
    return cv2.resize((image[y: (y + (h / 4)) + (h + (h / 4)),
                       x: (x + (w / 4)) + (w + (w / 4))]), (64, 128))


def frame2base64png(frame):
    return base64.b64encode(np.array(cv2.imencode('.png', frame)[1]).tostring())
