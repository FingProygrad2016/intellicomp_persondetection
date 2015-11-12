import numpy as np
import cv2


class BackgroundSubtractorMOG2:
    subtractor = None

    def __init__(self):
        self.subtractor = cv2.createBackgroundSubtractorMOG2(history=500)

    def apply(self, raw_image):
        # Convierto imagen a escalas de grices
        bg = cv2.cvtColor(raw_image, cv2.COLOR_BGR2GRAY)

        # Aplico filtro Blur
        bg = cv2.GaussianBlur(bg, (11, 11), 0)

        # Aplico la deteccion de fondo, esto tiene en cuenta el o los frames
        # previamente cargados
        bg = self.subtractor.apply(bg, 0.3, 0.05)

        # Erosiono y dilato el resultado para eliminar el ruido
        bg = cv2.erode(bg, np.ones((2, 2), np.uint8), iterations=3)
        bg = cv2.dilate(bg, np.ones((4, 1), np.uint8), iterations=1)
        bg = cv2.dilate(bg, np.ones((4, 2), np.uint8), iterations=1)
        bg = cv2.dilate(bg, np.ones((2, 3), np.uint8), iterations=1)
        # bg = cv2.morphologyEx(src=bg, op=cv2.MORPH_CLOSE,
        #                       kernel=np.ones((1,1),np.uint8), iterations=2)

        return bg


class BackgroundSubtractorKNN:

    def __init__(self, history, dist_2_threshold, n_samples, knn_samples, detect_shadows, shadow_threshold):

        self.subtractor = cv2.createBackgroundSubtractorKNN()

        # Sets the number of last frames that affect the background model.
        self.subtractor.setHistory(history)

        # Sets the threshold on the squared distance between the pixel and the sample. \
        # The threshold on the squared distance between the pixel and the sample to decide \
        # whether a pixel is close to a data sample.
        self.subtractor.setDist2Threshold(dist_2_threshold)

        # Sets the shadow detection flag. \
        # If true, the algorithm detects shadows and marks them.
        self.subtractor.setDetectShadows(detect_shadows)

        # Sets the number of neighbours, the k in kNN. \
        # K is the number of samples that need to be within dist2Threshold in order \
        # to decide that that pixel is matching the kNN background model.
        # Sets the k in the kNN. How many nearest neighbors need to match.
        self.subtractor.setkNNSamples(knn_samples)

        # Sets the shadow threshold. A shadow is detected if pixel is a darker version \
        # of the background. The shadow threshold (Tau in the paper) is a threshold defining \
        # how much darker the shadow can be. Tau= 0.5 means that if a pixel is more than twice \
        # darker then it is not shadow. See Prati, Mikic, Trivedi and Cucchiarra, \
        # Detecting Moving Shadows...*, IEEE PAMI,2003.
        self.subtractor.setShadowThreshold(shadow_threshold)

        # Sets the number of data samples in the background model. \
        # The model needs to be reinitialized to reserve memory.
        self.subtractor.setNSamples(n_samples)

    def apply(self, raw_image):

        # Convierto imagen a escalas de grises
        bg = cv2.cvtColor(raw_image, cv2.COLOR_BGR2GRAY)

        # Aplico filtro Blur
        bg = cv2.GaussianBlur(bg, (3, 3), 0)

        # Aplico la deteccion de fondo, esto tiene en cuenta el o los frames
        # previamente cargados
        fgMaskKNN = self.subtractor.apply(bg, -1)

        # create NumPy arrays from the boundaries
        # white = np.array([255], dtype = "uint8")

        # find the colors within the specified boundaries
        # fgMaskKNN = cv2.inRange(fgMaskKNN, white, white)

        # Erosiono y dilato el resultado para eliminar el ruido
        erode_dilate = \
            cv2.erode(fgMaskKNN, np.ones((3, 3), np.uint8), iterations=1)
        erode_dilate = \
            cv2.dilate(erode_dilate, np.ones((4, 3), np.uint8), iterations=1)

        return erode_dilate
