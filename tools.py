"""
Modulo que contiene funciones de ayuda generales
"""


def get_pxl_color(raw_image, x, y, square=4):
    """
    Returns the average color in the square with center x and y.
    :param raw_image:
    :param x:
    :param y:
    :return:
    """
    return raw_image[x, y]