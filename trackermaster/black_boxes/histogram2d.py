import numpy as np

from trackermaster.config import config
from utils.tools import normalize_matrix

USE_CONFIDENCE_LEVELS = config.getboolean("USE_CONFIDENCE_LEVELS")
CONFIDENCE_LEVELS = (config.getfloat("CONFIDENCE_LEVEL_0"),
                     config.getfloat("CONFIDENCE_LEVEL_1"))
USE_SQUARE_REGION_FOR_VERIFY = config.getboolean("USE_SQUARE_REGION_FOR_VERIFY")
SQUARE_REGION_RADIUS = config.getint("SQUARE_REGION_RADIUS")


class Histogram2D:
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
        self.onePersonConfidenceMatrix = np.zeros_like(self.confidenceMatrix,
                                                       dtype=np.float64)
        self.updateMaximums = np.zeros_like(self.confidenceMatrix, dtype=np.int)

    def create_confidence_matrix(self, blob, count):
        widths, heights = [], []

        widths.append(blob[2])
        heights.append(blob[3])

        hist, xedges, yedges = \
            np.histogram2d(widths, heights, (self.xedges, self.yedges))

        if hist.any():
            np.add(self.confidenceMatrix,
                   hist * count, self.confidenceMatrix)
            if count == 1:
                np.add(self.onePersonConfidenceMatrix,
                       hist, self.onePersonConfidenceMatrix)

    def update_confidence_matrix(self, blobs):
        print("Update histogram!!!")

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

    def verify_blob(self, pos):
        if USE_CONFIDENCE_LEVELS:
            # Level 0
            if self.confidenceMatrix[pos[0], pos[1]] >= CONFIDENCE_LEVELS[0]:
                if normalize_matrix(
                        self.onePersonConfidenceMatrix)[pos[0], pos[1]] >= \
                   CONFIDENCE_LEVELS[0]:
                    # No check is needed, there's one person
                    return False, True
                else:
                    # Check is needed, maybe more than one person
                    return True, True
            else:
                if USE_SQUARE_REGION_FOR_VERIFY:
                    x_min = max(0, pos[0] - SQUARE_REGION_RADIUS)
                    y_min = max(0, pos[1] - SQUARE_REGION_RADIUS + 1)
                    x_max = min(self.confidenceMatrix.shape[0],
                                pos[0] + SQUARE_REGION_RADIUS) + 1
                    y_max = min(self.confidenceMatrix.shape[1],
                                pos[1] + SQUARE_REGION_RADIUS) + 1
                    max_around = \
                        self.confidenceMatrix[x_min:x_max, y_min:y_max].max()

                # Level 1
                if self.confidenceMatrix[pos[0], pos[1]] >= \
                   CONFIDENCE_LEVELS[1]:
                    if USE_SQUARE_REGION_FOR_VERIFY and \
                       max_around >= CONFIDENCE_LEVELS[0]:
                        if normalize_matrix(
                                self.onePersonConfidenceMatrix)[pos[0], pos[1]]\
                                >= CONFIDENCE_LEVELS[0]:
                            # No check is needed, there's one person
                            return False, True
                        else:
                            # Check is needed, maybe more than one person
                            return True, True
                    else:
                        # Check is needed, there maybe a person
                        return True, False
                # Level 0
                else:
                    if USE_SQUARE_REGION_FOR_VERIFY and \
                       max_around >= CONFIDENCE_LEVELS[0]:
                        # Check is needed, there maybe a person
                        return True, False
                    else:
                        # No check is needed, there's no person
                        return False, False
        else:
            # If > 0, there maybe a person
            return self.confidenceMatrix[pos[0], pos[1]] > 0, False
