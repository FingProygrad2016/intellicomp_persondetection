"""
Modulo que contiene funciones de ayuda generales
"""
import base64
import cv2
import numpy as np
from math import sqrt, pow

MAX_WIDTH = 320
MAX_HEIGHT = 240


def get_avg_color(image, bg_subtraction_image, rect):
    """
    Returns the average color in the rectangle.
    :param image:
    :param bg_subtraction_image:
    :param rect: coordinates of rectangle containing pixels to average color
    :return:
    """

    return get_avg_color_in_pixels(
        apply_inverted_mask_to_image(
            crop_image_with_rect(image, rect),
            crop_image_with_rect(bg_subtraction_image, rect)
        )
    )


def get_avg_color_in_pixels(pixels):
    """
    Returns the average color in the pixels.
    :param pixels:
    :return:
    """
    r = 0
    g = 0
    b = 0
    count = 0
    for pixel in pixels:
        if not (np.array_equal(pixel, [0, 0, 0]) or np.array_equal(pixel, [255, 255, 255])):
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]
            count += 1
    if count > 0:
        average = (r/count, g/count, b/count)
    else:
        average = (0, 0, 0)

    return average


def apply_inverted_mask_to_image(image, inverted_mask):
    """
    Returns the pixels of the image with the inverted mask applied on it
    :param image:
    :param inverted_mask: matrix with the same size as the image, containing 0s and higher values
    :return: image pixels which overlaps with non 0s in the inverted mask
    """
    m = np.ma.masked_where(inverted_mask == 0, inverted_mask)
    pixels_left = np.ma.masked_array(image, m.mask)
    return np.ma.filled(np.ma.concatenate(pixels_left), 0)


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


def crop_image_with_rect(image, rect):
    """
    Crop an image
    :param image: the original image
    :param rect: rectangle to crop
    :return: the image cropped
        None is the area if the rectangle is 0
    """

    ((x1, y1), (x2, y2)) = rect

    return image[y1:y2, x1:x2]


def crop_image_for_person_detection(image, rect, border_around_blob):
    """
    Crop an image generating a frame (border) around
    :param image: the original image
    :param rect: rectangle to crop
    :return: the image cropped with the frame (border) around
        None is the area if the rectangle is 0
    """

    (x, y, w, h) = rect

    h_frame = h * border_around_blob[0]
    w_frame = w * border_around_blob[1]
    y_top = np.max((y - h_frame, 0))
    x_top = np.max((x - w_frame, 0))
    x_bottom = np.min((x + w + w_frame, image.shape[1]))
    y_bottom = np.min((y + h + h_frame, image.shape[0]))

    height_with_frame = abs(y_top - y_bottom)
    width_with_frame = abs(x_top - x_bottom)

    if (128 / width_with_frame) > (256 / height_with_frame):
        fact = (128 / width_with_frame)
    else:
        fact = (256 / height_with_frame)
    resize = (int(round(width_with_frame * fact)),
              int(round(height_with_frame * fact)))

    y_top = int(y_top)
    x_top = int(x_top)
    x_bottom = int(x_bottom)
    y_bottom = int(y_bottom)

    return cv2.resize((image[y_top:y_bottom, x_top:x_bottom]), resize), \
        (x_top, y_top, width_with_frame, height_with_frame), fact


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
