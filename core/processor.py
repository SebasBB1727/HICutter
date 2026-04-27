"""Processing helpers for HICutter.

This module contains the image processing logic separated from the UI.
"""

from typing import Any

import numpy as np
import cv2


def process_perspective_crop(cv_image: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Compute perspective transform from 4 points and return the warped image.

    Args:
        cv_image: Source OpenCV image (BGR numpy array).
        points: Array-like with shape (4,2) of image coordinates (float32).

    Returns:
        The warped (cropped) image as a numpy.ndarray.

    Raises:
        ValueError: If `points` does not contain 4 points or computed dimensions
            are invalid (non-positive).
    """
    pts = np.array(points, dtype=np.float32)
    if pts.shape[0] != 4:
        raise ValueError("Se requieren 4 puntos para el recorte de perspectiva")

    def _dist(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.linalg.norm(a - b))

    widthA = _dist(pts[2], pts[3])
    widthB = _dist(pts[1], pts[0])
    maxWidth = max(int(round(widthA)), int(round(widthB)))

    heightA = _dist(pts[1], pts[2])
    heightB = _dist(pts[0], pts[3])
    maxHeight = max(int(round(heightA)), int(round(heightB)))

    if maxWidth <= 0 or maxHeight <= 0:
        raise ValueError("Dimensiones inválidas calculadas para el recorte (ancho/alto <= 0)")

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1],
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(cv_image, M, (maxWidth, maxHeight), flags=cv2.INTER_LANCZOS4)
    return warped
