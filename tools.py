"""
Modulo que contiene funciones de ayuda generales
"""


def get_avg_color(raw_image, point, square_width=4):
    """
    Returns the average color in the square with center x and y.
    :param raw_image:
    :param point: Tuple (x, y) with the center of the square
    :param square: width of the square where to take the average
    :return:
    """
    # TODO: average
    return raw_image[point[1], point[0]]