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
        # bg = cv2.morphologyEx(src=bg, op=cv2.MORPH_OPEN,
        #                       kernel=np.ones((3,3),np.uint8), iterations=1)
        # bg = cv2.morphologyEx(src=bg, op=cv2.MORPH_CLOSE,
        #                       kernel=np.ones((1,1),np.uint8), iterations=2)

        return bg


class BackgroundSubtractorKNN:
    subtractor = None

    def __init__(self):
        self.subtractor = cv2.createBackgroundSubtractorKNN(history=250, dist2Threshold=350, detectShadows=False)
        self.subtractor.setkNNSamples(7)
        self.subtractor.setShadowThreshold(0.5)

    def apply(self, raw_image):
        #self.subtractor.SetNSamples(100)
        #self.subtractor.setkNNSamples(25)
        #self.subtractor.setShadowThreshold(0.5)

        # Convierto imagen a escalas de grices
        bg = cv2.cvtColor(raw_image, cv2.COLOR_BGR2GRAY)

        # Aplico filtro Blur
        # bg = cv2.GaussianBlur(bg, (11, 11), 0)

        # Redimensiono la imagen
        resized = cv2.resize(bg, (320, 240))

        # Aplico la deteccion de fondo, esto tiene en cuenta el o los frames
        # previamente cargados
        fgMaskKNN = self.subtractor.apply(bg, -1)

        # Erosiono y dilato el resultado para eliminar el ruido
        erode_dilate = cv2.erode(fgMaskKNN, np.ones((3, 3), np.uint8), iterations=1)
        erode_dilate = cv2.dilate(erode_dilate, np.ones((3, 3), np.uint8), iterations=1)

        cv2.imshow("bg", bg)
        cv2.imshow("fgMaskKNN", fgMaskKNN)
        cv2.imshow("erode_dilate", erode_dilate)

        return bg
