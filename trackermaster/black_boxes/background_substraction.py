import numpy as np
import cv2

from trackermaster.config import config


class BackgroundSubtractorMOG2:
    subtractor = None

    def __init__(self):
        self.gaussian_size = (config.getint('GAUSSIANBLUR_SIZE_X'),
                              config.getint('GAUSSIANBLUR_SIZE_Y'))
        self.erode_size = np.ones((config.getint('ERODE_SIZE_X'),
                                   config.getint('ERODE_SIZE_Y')), np.uint8)
        self.erode_times = config.getint('ERODE_TIMES')
        self.dilate_size = np.ones((config.getint('DILATE_SIZE_X'),
                                    config.getint('DILATE_SIZE_Y')), np.uint8)
        self.dilate_times = config.getint('DILATE_TIMES')
        self.history = config.getint('HISTORY')
        self.detect_shadows = config.getboolean('DETECT_SHADOWS')
        self.learning_rate = config.getfloat('MOG2_LEARNING_RATE')

        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.history, detectShadows=self.detect_shadows)

    def apply(self, raw_image):
        # Convierto imagen a escalas de grices
        bg = cv2.cvtColor(raw_image, cv2.COLOR_BGR2GRAY)

        # Aplico filtro Blur
        bg = cv2.GaussianBlur(bg, self.gaussian_size, 0)

        # Aplico la deteccion de fondo, esto tiene en cuenta el o los frames
        # previamente cargados
        bg = self.subtractor.apply(bg, 0.3, self.learning_rate)

        # Erosiono y dilato el resultado para eliminar el ruido
        bg = cv2.erode(bg, self.erode_size, iterations=self.erode_times)
        bg = cv2.dilate(bg, self.erode_size, iterations=self.erode_times)

        return bg


class BackgroundSubtractorKNN:

    def __init__(self):

        # Configuration parameters
        self.gaussian_size = (config.getint('GAUSSIANBLUR_SIZE_X'),
                              config.getint('GAUSSIANBLUR_SIZE_Y'))
        self.erode_size = np.ones((config.getint('ERODE_SIZE_X'),
                                   config.getint('ERODE_SIZE_Y')), np.uint8)
        self.erode_times = config.getint('ERODE_TIMES')
        self.dilate_size = np.ones((config.getint('DILATE_SIZE_X'),
                                    config.getint('DILATE_SIZE_Y')), np.uint8)
        self.dilate_times = config.getint('DILATE_TIMES')

        self.history = config.getint('HISTORY')
        self.dist_2_threshold = config.getint('DIST_2_THRESHOLD')
        self.n_samples = config.getint('N_SAMPLES')
        self.knn_samples = config.getint('KNN_SAMPLES')
        self.detect_shadows = config.getboolean('DETECT_SHADOWS')
        self.shadow_threshold = config.getfloat('SHADOW_THRESHOLD')

        self.subtractor = cv2.createBackgroundSubtractorKNN()

        # Sets the number of last frames that affect the background model.
        self.subtractor.setHistory(self.history)

        # Sets the threshold on the squared distance between the pixel and
        # the sample. The threshold on the squared distance between the
        # pixel and the sample to decide \
        # whether a pixel is close to a data sample.
        self.subtractor.setDist2Threshold(self.dist_2_threshold)

        # Sets the shadow detection flag. \
        # If true, the algorithm detects shadows and marks them.
        self.subtractor.setDetectShadows(self.detect_shadows)

        # Sets the number of neighbours, the k in kNN. \
        # K is the number of samples that need to be within dist2Threshold
        # in order \
        # to decide that that pixel is matching the kNN background model.
        # Sets the k in the kNN. How many nearest neighbors need to match.
        self.subtractor.setkNNSamples(self.knn_samples)

        # Sets the shadow threshold. A shadow is detected if pixel is a
        # darker version of the background. The shadow threshold
        # (Tau in the paper) is a threshold defining how much darker the
        # shadow can be. Tau= 0.5 means that if a pixel is more than twice \
        # darker then it is not shadow. See Prati, Mikic,
        # Trivedi and Cucchiarra, \
        # Detecting Moving Shadows...*, IEEE PAMI,2003.
        self.subtractor.setShadowThreshold(self.shadow_threshold)
        self.subtractor.setShadowValue(0)

        # Sets the number of data samples in the background model. \
        # The model needs to be reinitialized to reserve memory.
        self.subtractor.setNSamples(self.n_samples)

    def apply(self, raw_image):

        # Convierto imagen a escalas de grises
        bg = cv2.cvtColor(raw_image, cv2.COLOR_BGR2GRAY)

        # Aplico filtro Blur
        bg = cv2.GaussianBlur(bg, self.gaussian_size, 0)

        # Aplico la deteccion de fondo, esto tiene en cuenta el o los frames
        # previamente cargados
        fgmaskknn = self.subtractor.apply(bg, -1)

        # Erode and Dilate the results for removing the noise
        erode_dilate = cv2.erode(fgmaskknn, self.erode_size,
                                 iterations=self.erode_times)
        erode_dilate = cv2.dilate(erode_dilate, self.dilate_size,
                                  iterations=self.dilate_times)

        return erode_dilate
