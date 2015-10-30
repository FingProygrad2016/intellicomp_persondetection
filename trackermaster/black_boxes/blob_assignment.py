import numpy
from munkres import Munkres

from utils.tools import euclidean_distance


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

    def get_costs(self, k_filters):

        # the costs matrix width has to be larger or equal than height
        columns_count = len(k_filters) # max(len(self.blobs), len(k_filters))

        costs_matrix = numpy.zeros(shape=(len(self.blobs), columns_count))

        assigned_kalman_filter = numpy.empty(shape=columns_count)
        assigned_kalman_filter.fill(-1)
        assigned_blob = numpy.empty(shape=len(self.blobs), dtype=int)
        assigned_blob.fill(-1)

        for i in range(0, len(self.blobs)):
            costs_row = numpy.zeros(shape=columns_count)
            for j in range(0, len(k_filters)):
                prediction = k_filters[j].kalman_filter.statePost
                distance = euclidean_distance((prediction[0], prediction[1]), self.blobs[i].pt)
                costs_row[j] = distance
                if distance <= self.distance_threshold:
                    assigned_kalman_filter[j] = 0
                    assigned_blob[i] = 0
            # for j in range(len(k_filters), columns_count):
            #     costs_row[j] = 100000
            costs_matrix[i] = costs_row

        columns_relation = []
        columns_to_delete = []
        rows_to_delete = []
        j = 0
        for i in range(0, len(assigned_kalman_filter)):
            if assigned_kalman_filter[i] == -1:
                columns_to_delete.append(i)
            else:
                columns_relation.append((j, i)) # column j corresponds to original kalman filter i
                j += 1
        for i in range(0, len(assigned_blob)):
            if assigned_blob[i] == -1:
                rows_to_delete.append(i)

        costs_matrix = numpy.delete(costs_matrix, columns_to_delete, axis=1)
        costs_matrix = numpy.delete(costs_matrix, rows_to_delete, axis=0)

        valid_kalman_filters_amount = costs_matrix.shape[1]
        new_kalman_filters = costs_matrix.shape[0] - costs_matrix.shape[1]
        if new_kalman_filters > 0:
            # more blobs than filters
            a = numpy.empty((costs_matrix.shape[0], new_kalman_filters))
            a.fill(100000)
            costs_matrix = numpy.append(costs_matrix, a, axis=1)

        return costs_matrix, assigned_blob, valid_kalman_filters_amount, columns_relation

    def apply(self, k_filters):
        assigned_blob = []

        if len(k_filters) > 0 and len(self.blobs) > 0:
            m = Munkres()

            costs, assigned_blob, valid_kalman_filters_amount, columns_relation = self.get_costs(k_filters)
            if (costs.size > 0) & (costs.__len__() > 0):
                indexes = m.compute(costs.copy())

                j = 0
                for i in range(0, len(assigned_blob)):
                    if assigned_blob[i] == 0:
                        column = indexes[j][1]
                        if column < valid_kalman_filters_amount and costs[j][column] <= self.distance_threshold:
                            assigned_blob[i] = columns_relation[column][1]
                        else:
                            assigned_blob[i] = -1

                        j += 1

        return assigned_blob


class HungarianAlgorithmBlobSize:

    size_threshold = -1
    blobs = []

    def __init__(self, size_threshold, blobs):
        self.size_threshold = size_threshold
        self.blobs = blobs

    def get_costs(self, k_filters):

        # the costs matrix width has to be larger or equal than height
        columns_count = max(len(self.blobs), len(k_filters))

        costs_matrix = numpy.zeros(shape=(len(self.blobs), columns_count))

        for i in range(0, len(self.blobs)):
            costs_row = numpy.zeros(shape=columns_count)
            for j in range(0, len(k_filters)):
                size = k_filters[j].size
                costs_row[j] = abs(self.blobs[i].size - size)
            for j in range(len(k_filters), columns_count):
                costs_row[j] = 100000
            costs_matrix[i] = costs_row

        return costs_matrix

    def apply(self, k_filters):
        result = []

        if len(k_filters) > 0 and len(self.blobs) > 0:
            m = Munkres()

            costs = self.get_costs(k_filters)
            if (costs.size > 0) & (costs.__len__() > 0):
                indexes = m.compute(costs.copy())
                for row, column in indexes:
                    if column < len(k_filters) and costs[row][column] <= self.size_threshold:
                        result.append((row, column))
                    else:
                        result.append((row, -1))

        return result
