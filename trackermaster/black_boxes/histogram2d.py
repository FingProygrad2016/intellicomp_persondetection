import numpy as np


class Histogram2D:
    detector = None
    confidenceMatrix = None

    def __init__(self, shape):
        self.confidenceMatrix = np.zeros(shape=shape, dtype=np.float64)
        self.xedges =\
            np.linspace(0, self.confidenceMatrix.shape[0] * 10,
                        self.confidenceMatrix.shape[0] + 1, endpoint=True)
        self.yedges =\
            np.linspace(0, self.confidenceMatrix.shape[1] * 10,
                        self.confidenceMatrix.shape[1] + 1, endpoint=True)

    def create_confidence_matrix(self, blob, count):
        widths, heights = [], []

        widths.append(blob[2])
        heights.append(blob[3])

        hist, xedges, yedges = \
            np.histogram2d(widths, heights, (self.xedges, self.yedges))

        if hist.any():
            np.add(self.confidenceMatrix, hist * count,
                   out=self.confidenceMatrix)

        return self.confidenceMatrix

    def update_confidence_matrix(self, blobs):
        print("Update histogram!!!")
        for row_index, row in enumerate(self.confidenceMatrix):
            self.confidenceMatrix[row_index] = \
                np.array(list(map(lambda x: max(x - 1, 0), row)))

        for blob in blobs:
            if blob[1] > 0:
                self.confidenceMatrix = \
                    self.create_confidence_matrix((blob[2][0], blob[2][1],
                                                   blob[3][0], blob[3][1]),
                                                  len(blob[0]))
        return self.confidenceMatrix
