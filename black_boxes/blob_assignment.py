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
        costs_matrix = numpy.zeros(shape=(self.blobs.__len__(), k_filters.__len__()))

        for i in range(0, self.blobs.__len__()):
            costs_row = numpy.zeros(shape=(k_filters.__len__()))
            for j in range(0, k_filters.__len__()):
                prediction = k_filters[j].kalman_filter.statePost
                costs_row[j] = euclidean_distance((prediction[0], prediction[1]), self.blobs[i].pt)
            costs_matrix[i] = costs_row
        return costs_matrix

    def apply(self, k_filters):
        result = []
        m = Munkres()

        costs = self.getCosts(k_filters)
        if (costs.size > 0) & (costs.__len__() > 0):
            indexes = m.compute(costs)
            for row, column in indexes:
                if costs[row][column] <= self.distance_threshold:
                    result.append((row, column))
        return result
