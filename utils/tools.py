"""
Modulo que contiene funciones de ayuda generales
"""
import base64
import cv2
import numpy as np
from math import sqrt, pow

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
        None is the area if the rectangle is 0
    """

    (x, y, w, h) = rect

    h_frame = h / 4
    w_frame = w / 4
    y_top = int(np.max((y - h_frame, 0)))
    x_top = int(np.max((x - w_frame, 0)))
    y_bottom = int(np.min((y + h + h_frame, image.shape[0])))
    x_bottom = int(np.min((x + w + w_frame, image.shape[1])))

    height_with_frame = abs(y_top - y_bottom)
    width_with_frame = abs(x_top - x_bottom)

    if (128 / w) > (256 / h):
        fact = (128 / w)
    else:
        fact = (256 / h)
    resize = (int(round(w * fact)), int(round(h * fact)))

    return cv2.resize((image[y_top:y_bottom, x_top:x_bottom]), resize), \
        (x_top * fact, y_top * fact, width_with_frame * fact, height_with_frame * factq), fact


def crop_image_for_person_detection2(image, rect):
    """
    Crop an image generating a frame (border) around
    :param image: the original image
    :param rect: rectangle to crop
    :return: the image cropped with the frame (border) around
        None is the area if the rectangle is 0
    """

    (x, y, w, h) = rect

    if w < 8 or h < 8:
        return None, 0, 0, 0, 0, 0
    # Add a frame around the rectangle
    h_frame = h / 4
    w_frame = w / 4
    y_top = int(np.max(y - h_frame, 0))
    x_top = int(np.max(x - w_frame, 0))
    y_bottom = int(np.min((y + h + h_frame), image.shape[0]))
    x_bottom = int(np.min(x + w + w_frame, image.shape[1]))

    height = abs(y_top - y_bottom)
    width = abs(x_top - x_bottom)

    if width < 10 or height < 10:
        return None, 0, 0, 0, 0, 0

    d128_width = (128/width)
    d256_height = (256/height)

    # If width and height are greater than the looked rectangle, process it
    # as it is
    if d128_width <= 1 and d256_height <= 1:
        mult = 1
    elif d128_width > d256_height:
        mult = d128_width
    else:
        mult = d256_height

    mult = 1 if mult < 1 else mult
    # print("WIDTH: %s HEIGHT: %s" % (width, height))

    cropped_image = image[y_top:y_bottom, x_top:x_bottom]

    return cv2.resize(cropped_image, (int(width*mult), int(height*mult))), \
        x_top, y_top, width, height, mult

    # return cv2.resize(cropped_image, (128, 256)), \
    #     x_top, y_top, width, height, mult


def rect_size(rect):
    return sqrt(pow(rect[2], 2) + pow(rect[3], 2))


def frame2base64png(frame):
    return base64.b64encode(np.array(cv2.imencode('.png', frame)[1]).tostring())


def x1y1x2y2_to_x1y1wh_single(rectangle):
    # Transform a rectangle expressed as (x1,y1,x2,y2) to (x1,y1, width, height)
    return rectangle[0], rectangle[1], rectangle[2] - rectangle[0], \
           rectangle[3] - rectangle[1]


def x1y1wh_to_x1y1x2y2_single(rectangle):
    # Transform a rectangle expressed as (x1,y1, width, height) to (x1,y1,x2,y2)
    return rectangle[0], rectangle[1], rectangle[0] + rectangle[2], \
           rectangle[1] + rectangle[3]


def x1y1x2y2_to_x1y1wh(rectangles):
    return np.apply_along_axis(x1y1x2y2_to_x1y1wh_single, 1, rectangles)


def x1y1wh_to_x1y1x2y2(rectangles):
    return np.apply_along_axis(x1y1wh_to_x1y1x2y2_single, 1, rectangles)
