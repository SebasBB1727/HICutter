from __future__ import annotations

from typing import Optional, Tuple

from PyQt6 import QtCore, QtGui


class ScaledPixmapManager:
    """Helper to manage a QPixmap scaled cache and offsets for a widget.

    This centralizes the logic previously embedded in `ImageCanvas` for
    computing the scaled pixmap and converting coordinates between widget
    space and image space.
    """

    def __init__(self) -> None:
        self._pixmap: Optional[QtGui.QPixmap] = None
        self._scaled_pixmap_cache: Optional[QtGui.QPixmap] = None
        self._scaled_pixmap_left: int = 0
        self._scaled_pixmap_top: int = 0

    def set_pixmap(self, pixmap: Optional[QtGui.QPixmap]) -> None:
        self._pixmap = pixmap
        self._scaled_pixmap_cache = None
        self._scaled_pixmap_left = 0
        self._scaled_pixmap_top = 0

    def update_scaled_cache(self, widget_size: QtCore.QSize) -> None:
        """Update the scaled pixmap cache and left/top offsets for centering.

        Call this when the source pixmap changes or the widget is resized.
        """
        if self._pixmap is None:
            self._scaled_pixmap_cache = None
            self._scaled_pixmap_left = 0
            self._scaled_pixmap_top = 0
            return

        scaled = self._pixmap.scaled(widget_size, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        left = (widget_size.width() - scaled.width()) // 2
        top = (widget_size.height() - scaled.height()) // 2
        self._scaled_pixmap_cache = scaled
        self._scaled_pixmap_left = left
        self._scaled_pixmap_top = top

    def get_scaled_and_offset(self) -> Tuple[Optional[QtGui.QPixmap], int, int]:
        return self._scaled_pixmap_cache, self._scaled_pixmap_left, self._scaled_pixmap_top

    def widget_to_image_coords(self, wx: float, wy: float) -> Optional[Tuple[float, float]]:
        """Convert widget coordinates to image coordinates (float).

        Returns None when the widget point falls outside the displayed image.
        """
        if self._pixmap is None:
            return None

        scaled, left, top = self.get_scaled_and_offset()
        if scaled is None:
            return None

        if not (left <= wx <= left + scaled.width() and top <= wy <= top + scaled.height()):
            return None

        rel_x = wx - left
        rel_y = wy - top

        orig_w = self._pixmap.width()
        orig_h = self._pixmap.height()

        img_x = rel_x * (orig_w / scaled.width())
        img_y = rel_y * (orig_h / scaled.height())
        return float(img_x), float(img_y)

    def image_to_widget_coords(self, ix: float, iy: float) -> Optional[Tuple[int, int]]:
        if self._pixmap is None:
            return None
        scaled, left, top = self.get_scaled_and_offset()
        if scaled is None:
            return None
        orig_w = self._pixmap.width()
        orig_h = self._pixmap.height()
        wx = left + int(ix * (scaled.width() / orig_w))
        wy = top + int(iy * (scaled.height() / orig_h))
        return wx, wy
