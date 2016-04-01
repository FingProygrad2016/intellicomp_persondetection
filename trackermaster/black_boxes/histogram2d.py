import numpy as np


class Histogram2D:
    detector = None
    confidenceMatrix = None
    widths = []
    heights = []
    c = None

    def __init__(self):
        self.confidenceMatrix = np.zeros(shape=(32, 24), dtype=np.int32)

    def create_confidence_matrix(self, blob):
        # TODO: Agregar arreglos x e y para mantener las medidas de las personas
        widths, heights = [], []
        xedges, yedges = np.linspace(0, 320, 32, endpoint=True),\
            np.linspace(0, 240, 24, endpoint=True)

        self.widths.append(blob[2])
        self.heights.append(blob[3])

        hist, xedges, yedges = \
            np.histogram2d(self.widths, self.heights, (xedges, yedges))

        if self.confidenceMatrix.any():
            np.add(self.confidenceMatrix, hist, out=self.confidenceMatrix)
        else:
            self.confidenceMatrix = hist

        xidx = np.clip(np.digitize(widths, xedges), 0, hist.shape[0] - 1)
        yidx = np.clip(np.digitize(heights, yedges), 0, hist.shape[1] - 1)
        self.c = self.confidenceMatrix[xidx, yidx]

        return self.confidenceMatrix
