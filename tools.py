"""
Modulo que contiene funciones de ayuda generales
"""


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