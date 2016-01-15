"""
Modulo que contiene funciones de ayuda generales
"""
import cv2

MAX_HEIGHT = 480
MAX_WIDTH = 640


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
    return pow(abs(sum(map(lambda x_y: (x_y[0]-x_y[1])**2, zip(point1, point2)))), 0.5)


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
    im2, contours, hierarchy = cv2.findContours(bg_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    bounding_boxes = []
    for contour in contours:
        bounding_boxes.append(cv2.boundingRect(contour))
    return bounding_boxes


def crop_image_with_frame(image, rect, frame_width, frame_height):
    """
    Crop an image generating a frame around
    :param image: the original image
    :param rect: rectangle to crop
    :param frame_width: width of the frame
    :param frame_height: height of the frame
    :return: the image cropped with the frame around
    """

    (x, y, w, h) = (rect[0], rect[1], rect[2], rect[3])
    if (y - frame_height) > 0:
        y -= frame_height
    else:
        y = 0
    if (x - frame_width) > 0:
        x -= frame_width
    else:
        x = 0

    # NOTE: its img[y: y + h, x: x + w] and *not* img[x: x + w, y: y + h]
    return image[y: (y + 8) + (h + 8), x: (x + 4) + (w + 4)]
