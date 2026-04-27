from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np


class PointManager:
    """Manage a small list of image points and provide ordering logic.

    This centralizes point addition/removal/reset and the `_order_points`
    heuristic that orders 4 points as top-left, top-right, bottom-right,
    bottom-left.
    """

    def __init__(self) -> None:
        self.points: List[Tuple[float, float]] = []

    def add_point(self, pt: Tuple[float, float]) -> None:
        self.points.append((float(pt[0]), float(pt[1])))

    def pop_last(self) -> Optional[Tuple[float, float]]:
        if not self.points:
            return None
        return self.points.pop()

    def reset(self) -> None:
        self.points = []

    def __len__(self) -> int:
        return len(self.points)

    def get_points(self) -> np.ndarray:
        pts = np.array(self.points, dtype=np.float32)
        if pts.shape[0] == 4:
            return self._order_points(pts)
        return pts

    def finalize_if_full(self) -> Optional[np.ndarray]:
        """If 4 points are present, order them, update internal list, and return the ordered array."""
        if len(self.points) == 4:
            pts = np.array(self.points, dtype=np.float32)
            ordered = self._order_points(pts)
            self.points = [tuple(p) for p in ordered.tolist()]
            return ordered
        return None

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        pts = np.array(pts, dtype=np.float32)
        if pts.shape[0] != 4:
            return pts.copy()

        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # top-left  (min sum)
        rect[2] = pts[np.argmax(s)]  # bottom-right (max sum)

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right (min diff)
        rect[3] = pts[np.argmax(diff)]  # bottom-left (max diff)

        return rect
