import numpy
from munkres import Munkres
from tools import euclidean_distance

__author__ = 'ismael'

# Referencias en:
# https://pypi.python.org/pypi/munkres/
# http://answers.opencv.org/question/9354/kalman-filter-solution-to-some-cases/
# http://www.math.harvard.edu/archive/20_spring_05/handouts/assignment_overheads.pdf


class HungarianAlgorithmBlobPosition:

    distance_threshold = -1
    blobs = []

    def __init__(self, distance_threshold, blobs):
        self.distance_threshold = distance_threshold
        self.blobs = blobs

    def getCosts(self, k_filters):
        # Matriz de costos

        # the matrix width has to be larger or equal than height
        columns_count = max(len(self.blobs), len(k_filters))

        costs_matrix = numpy.zeros(shape=(len(self.blobs), columns_count))

        for i in range(0, len(self.blobs)):
            costs_row = numpy.zeros(shape=(columns_count))
            for j in range(0, len(k_filters)):
                prediction = k_filters[j].kalman_filter.statePost
                costs_row[j] = euclidean_distance((prediction[0], prediction[1]), self.blobs[i].pt)
            for j in range(len(k_filters), columns_count):
                costs_row[j] = 100000
            costs_matrix[i] = costs_row

        return costs_matrix

    def apply(self, k_filters):
        result = []

        if len(k_filters) > 0 and len(self.blobs) > 0:
            m = Munkres()

            costs = self.getCosts(k_filters)
            if (costs.size > 0) & (costs.__len__() > 0):
                indexes = m.compute(costs.copy())
                for row, column in indexes:
                    if column < len(k_filters) and costs[row][column] <= self.distance_threshold:
                        result.append((row, column))
                    else:
                        result.append((row, -1))

        return result
