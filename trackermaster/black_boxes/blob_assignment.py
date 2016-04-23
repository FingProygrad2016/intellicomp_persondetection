import numpy as np
from munkres import Munkres
import math

# References in:
# https://pypi.python.org/pypi/munkres/
# http://answers.opencv.org/question/9354/kalman-filter-solution-to-some-cases/
# http://www.math.harvard.edu/archive/20_spring_05/handouts/assignment_overheads.pdf


class HungarianAlgorithm:

    def __init__(self, cost_function, threshold, infinite=100000):
        self.threshold = threshold
        self.infinite = infinite
        self.cost_function = cost_function

    def get_costs_generic(self, rows_data, columns_data, weights):

        # the costs matrix width has to be larger or equal than height
        columns_count = len(columns_data)  # max(len(self.blobs), len(k_filters))
        rows_count = len(rows_data)

        costs_matrix = np.zeros(shape=(rows_count, columns_count), dtype=float)

        assigned_column = np.empty(shape=columns_count, dtype=int)
        assigned_column.fill(-1)
        assigned_row = np.empty(shape=rows_count, dtype=int)
        assigned_row.fill(-1)

        for i in range(0, rows_count):
            costs_row = np.zeros(shape=columns_count, dtype=float)
            for j in range(0, columns_count):
                if weights:
                    cost = self.cost_function(rows_data[i], columns_data[j], weights)
                else:
                    cost = self.cost_function(rows_data[i], columns_data[j])
                if cost["valid"]:
                    assigned_column[j] = 0
                    assigned_row[i] = 0
                    costs_row[j] = cost["value"]
                else:
                    costs_row[j] = cost["value"] * (-1)
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

        costs_matrix = np.delete(costs_matrix, columns_to_delete, axis=1)
        costs_matrix = np.delete(costs_matrix, rows_to_delete, axis=0)

        valid_columns_amount = costs_matrix.shape[1]
        new_columns = costs_matrix.shape[0] - costs_matrix.shape[1]
        if new_columns > 0:
            # more rows than columns
            a = np.empty((costs_matrix.shape[0], new_columns))
            a.fill(-self.infinite)
            costs_matrix = np.append(costs_matrix, a, axis=1)

        return costs_matrix, assigned_row, valid_columns_amount, columns_relation

    def apply(self, rows_data, columns_data, weights=None):
        assigned_row = []
        assigned_row_cost = np.empty(shape=len(rows_data), dtype=float)
        assigned_row_cost.fill(-1.0)

        if len(rows_data) > 0:
            if len(columns_data) > 0:
                m = Munkres()

                costs, assigned_row, valid_columns_amount, columns_relation = \
                    self.get_costs_generic(rows_data, columns_data, weights)

                if costs.shape[0] > 0 and costs.shape[1]:
                    indexes = m.compute(np.absolute(costs))

                    j = 0
                    for i in range(0, len(assigned_row)):
                        if assigned_row[i] == 0:
                            column = indexes[j][1]
                            # math.copysign(1,-0.0) gives -1.0, and math.copysign(1,0.0) gives 1.0
                            if column < valid_columns_amount and math.copysign(1, costs[j][column]) == 1.0:
                                assigned_row[i] = columns_relation[column][1]
                            else:
                                assigned_row[i] = -1
                            assigned_row_cost[i] = abs(costs[j][column])

                            j += 1
            else:
                assigned_row = np.empty(shape=len(rows_data), dtype=int)
                assigned_row.fill(-1)

        return assigned_row, assigned_row_cost
