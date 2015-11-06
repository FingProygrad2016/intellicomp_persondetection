import numpy
from munkres import Munkres

# References in:
# https://pypi.python.org/pypi/munkres/
# http://answers.opencv.org/question/9354/kalman-filter-solution-to-some-cases/
# http://www.math.harvard.edu/archive/20_spring_05/handouts/assignment_overheads.pdf


class HungarianAlgorithm:

    def __init__(self, cost_function, threshold, infinite=100000):
        self.threshold = threshold
        self.infinite = infinite
        self.cost_function = cost_function

    def get_costs_generic(self, rows_data, columns_data):

        # the costs matrix width has to be larger or equal than height
        columns_count = len(columns_data)  # max(len(self.blobs), len(k_filters))
        rows_count = len(rows_data)

        costs_matrix = numpy.zeros(shape=(rows_count, columns_count))

        assigned_column = numpy.empty(shape=columns_count, dtype=int)
        assigned_column.fill(-1)
        assigned_row = numpy.empty(shape=rows_count, dtype=int)
        assigned_row.fill(-1)

        for i in range(0, rows_count):
            costs_row = numpy.zeros(shape=columns_count)
            for j in range(0, columns_count):
                cost = self.cost_function(rows_data[i], columns_data[j])
                costs_row[j] = cost
                if cost <= self.threshold:
                    assigned_column[j] = 0
                    assigned_row[i] = 0
            costs_matrix[i] = costs_row

        columns_relation = []
        columns_to_delete = []
        rows_to_delete = []
        j = 0
        for i in range(0, len(assigned_column)):
            if assigned_column[i] == -1:
                columns_to_delete.append(i)
            else:
                columns_relation.append((j, i))  # column j corresponds to original column_data i
                j += 1
        for i in range(0, len(assigned_row)):
            if assigned_row[i] == -1:
                rows_to_delete.append(i)

        costs_matrix = numpy.delete(costs_matrix, columns_to_delete, axis=1)
        costs_matrix = numpy.delete(costs_matrix, rows_to_delete, axis=0)

        valid_columns_amount = costs_matrix.shape[1]
        new_columns = costs_matrix.shape[0] - costs_matrix.shape[1]
        if new_columns > 0:
            # more rows than columns
            a = numpy.empty((costs_matrix.shape[0], new_columns))
            a.fill(self.infinite)
            costs_matrix = numpy.append(costs_matrix, a, axis=1)

        return costs_matrix, assigned_row, valid_columns_amount, columns_relation

    def apply(self, rows_data, columns_data):
        assigned_row = []

        if len(columns_data) > 0 and len(rows_data) > 0:
            m = Munkres()

            costs, assigned_row, valid_columns_amount, columns_relation = \
                self.get_costs_generic(rows_data, columns_data)

            if costs.shape[0] > 0 and costs.shape[1]:
                indexes = m.compute(costs.copy())

                j = 0
                for i in range(0, len(assigned_row)):
                    if assigned_row[i] == 0:
                        column = indexes[j][1]
                        if column < valid_columns_amount and costs[j][column] <= self.threshold:
                            assigned_row[i] = columns_relation[column][1]
                        else:
                            assigned_row[i] = -1

                        j += 1

        return assigned_row
