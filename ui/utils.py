from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from PyQt6 import QtGui
from utils.logger import setup_logger

logger = setup_logger(__name__)

def _cv_to_qpixmap(img: np.ndarray) -> QtGui.QPixmap:
    """Convert an OpenCV image (numpy array, BGR or grayscale) to QPixmap.

    Accepts images with shapes (H, W), (H, W, 1), (H, W, 3) or (H, W, 4).
    Performs color conversion BGR->RGB and BGRA->RGBA when needed.
    """
    if img is None:
        raise ValueError("img is None")

    h, w = img.shape[:2]
    # Grayscale
    if img.ndim == 2 or (img.ndim == 3 and img.shape[2] == 1):
        qimg = QtGui.QImage(img.tobytes(), w, h, w, QtGui.QImage.Format.Format_Grayscale8)
        return QtGui.QPixmap.fromImage(qimg)

    # 3-channel BGR -> RGB
    if img.ndim == 3 and img.shape[2] == 3:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * w
        qimg = QtGui.QImage(rgb.tobytes(), w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        return QtGui.QPixmap.fromImage(qimg)

    # 4-channel BGRA -> RGBA
    if img.ndim == 3 and img.shape[2] == 4:
        rgba = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
        bytes_per_line = 4 * w
        qimg = QtGui.QImage(rgba.tobytes(), w, h, bytes_per_line, QtGui.QImage.Format.Format_RGBA8888)
        return QtGui.QPixmap.fromImage(qimg)

    # Fallback: try to coerce to RGB
    try:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * w
        qimg = QtGui.QImage(rgb.tobytes(), w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        return QtGui.QPixmap.fromImage(qimg)
    except Exception as e:
        logger.error("Forma no soposrtada para converion a QPixmap", exc_info=True)
        raise ValueError("Unsupported image shape for conversion to QPixmap") from e
