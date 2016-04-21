import numpy as np

from utils.tools import normalize_matrix


class Histogram2D:
    detector = None

    def __init__(self, shape):
        self.confidenceMatrix = np.zeros(shape=(int(shape[0] / 5),
                                                int(shape[1] / 5)),
                                         dtype=np.float64)
        self.xedges =\
            np.linspace(0, int(self.confidenceMatrix.shape[0] * 5),
                        int(self.confidenceMatrix.shape[0]) + 1,
                        endpoint=True)
        self.yedges =\
            np.linspace(0, int(self.confidenceMatrix.shape[1] * 5),
                        int(self.confidenceMatrix.shape[1]) + 1,
                        endpoint=True)
        self.normalizedConfidenceMatrix = np.zeros_like(self.confidenceMatrix,
                                                        dtype=np.float64)
        self.updateMaximums = np.zeros_like(self.confidenceMatrix, dtype=np.int)

    def create_confidence_matrix(self, blob, count):
        widths, heights = [], []

        widths.append(blob[2])
        heights.append(blob[3])

        hist, xedges, yedges = \
            np.histogram2d(widths, heights, (self.xedges, self.yedges))

        if hist.any():
            np.add(self.confidenceMatrix, hist * count,
                   out=self.confidenceMatrix)

    def update_confidence_matrix(self, blobs):
        print("Update histogram!!!")
        # for row_index, row in enumerate(self.confidenceMatrix):
        #     self.confidenceMatrix[row_index] = \
        #         np.array(list(map(lambda x: max(x - 1, 0), row)))

        for blob in blobs:
            x = blob[2][0]
            y = blob[2][1]
            w = blob[3][0]
            h = blob[3][1]
            x_bin = int(w / 10)
            y_bin = int(h / 10)

            if blob[1] == 1:
                self.create_confidence_matrix((x, y, w, h), len(blob[0]))
                if self.confidenceMatrix[x_bin][y_bin] >= \
                        (self.confidenceMatrix.max() - 5):
                    self.updateMaximums[x_bin][y_bin] = 0
            else:
                if self.confidenceMatrix[x_bin][y_bin] >= \
                        (self.confidenceMatrix.max() - 5):
                    self.updateMaximums[x_bin][y_bin] += 1
                    if self.updateMaximums[x_bin][y_bin] == 3:  # MAX
                        self.confidenceMatrix[x_bin][y_bin] -= 1

        self.normalizedConfidenceMatrix = \
            normalize_matrix(self.confidenceMatrix)
