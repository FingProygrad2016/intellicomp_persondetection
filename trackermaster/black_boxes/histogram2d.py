import numpy as np


class Histogram2D:
    detector = None
    confidenceMatrix = None

    def __init__(self):
        self.confidenceMatrix = np.zeros(shape=(32, 24), dtype=np.int32)

    def create_confidence_matrix(self, blob):
        # TODO: Agregar arreglos x e y para mantener las medidas de las personas
        widths, heights = [], []
        xedges, yedges = np.linspace(0, 320, 32, endpoint=False),\
            np.linspace(0, 240, 24, endpoint=False)

        widths.append(blob[2])
        heights.append(blob[3])

        hist, xedges, yedges = \
            np.histogram2d(widths, heights, (xedges, yedges))

        if self.confidenceMatrix.any():
            np.add(self.confidenceMatrix, hist, out=self.confidenceMatrix)
        else:
            self.confidenceMatrix = hist

        return self.confidenceMatrix
