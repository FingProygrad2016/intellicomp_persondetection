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


def euclidean_distance(point1, point2):
    """
    Returns the euclidean distance between point 1 and 2.
    :param point1: Tuple with the position of the point 1
    :param point2: Tuple with the position of the point 2
    :return:
    """
    # FIXME: Ver si existe alternativa en Numpy (+ eficiente)
    return pow(abs(sum(map(lambda (x, y): (x-y)**2, zip(point1, point2)))), 0.5)


def enum(**enums):
    """
    Function to create new Enumerates
    (basically it creates a new Class 'Enum' without inheritence and with the
      attributes passed in 'enums')

    Example of use:
        Colors = enum(RED='Red', BLUE='Blue', YELLOW='Yellow')
        car1 = Car(color=Colors.RED)

    :param enums: Values of the enumerate passed as a dict.
    :return: A class called Enum with the attributes passed in enums.
    """
    return type('Enum', (), enums)