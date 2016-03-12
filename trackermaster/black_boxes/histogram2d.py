import numpy as np
print(np)


class Histogram2D:
    detector = None
    confidenceMatrix = None

    def __init__(self, shape):
        self.confidenceMatrix = np.zeros(shape=shape, dtype=np.float64)

    def create_confidence_matrix(self, blob):
        widths, heights = [], []
        xedges, yedges =\
            np.linspace(0, self.confidenceMatrix.shape[0] * 10,
                        self.confidenceMatrix.shape[0] + 1, endpoint=True),\
            np.linspace(0, self.confidenceMatrix.shape[1] * 10,
                        self.confidenceMatrix.shape[1] + 1, endpoint=True)

        widths.append(blob[2])
        heights.append(blob[3])

        hist, xedges, yedges = \
            np.histogram2d(widths, heights, (xedges, yedges))

        if hist.any():
            np.add(self.confidenceMatrix, hist, out=self.confidenceMatrix)

        return self.confidenceMatrix

    def update_confidence_matrix(self, blob):
        return self.confidenceMatrix
