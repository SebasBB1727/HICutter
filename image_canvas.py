from __future__ import annotations

from typing import List, Optional, Tuple

import cv2
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
from ui.components.geometry import ScaledPixmapManager
from ui.components.point_manager import PointManager
from ui.components.magnifier import MagnifierTool
from ui.components.sniper_mode import SniperModeManager
from ui.utils import _cv_to_qpixmap


class ImageCanvas(QtWidgets.QWidget):
    """Widget para mostrar una imagen y recoger 4 puntos de control.

    - Usa QPixmap para el renderizado (alta calidad) y mantiene la imagen OpenCV
      original en `self.cv_image`.
    - Emite la señal `fourPointsSelected` cuando el usuario ha seleccionado 4 puntos
      (coordenadas en el espacio de la imagen, formato float32, shape (4,2)).
    - Click izquierdo: añade punto (si está sobre la imagen). Click derecho: borra
      el último punto. Doble click con el botón izquierdo reinicia la selección.
    """
    fourPointsSelected = QtCore.pyqtSignal(object)
    requestLoadImage = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 240)

        self.cv_image: Optional[np.ndarray] = None
        self._pixmap: Optional[QtGui.QPixmap] = None
        # helpers
        self._scaled_manager = ScaledPixmapManager()
        self._point_manager = PointManager()

        # interacción/cursor
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self._mouse_in_img: bool = False
        self._mouse_wx: int = 0
        self._mouse_wy: int = 0
        self.cross_len: int = 8
        self._cross_cursor = self._create_cross_cursor(self.cross_len)
        # Caché del pixmap escalado está gestionada por `ScaledPixmapManager`
        # Lupa de enfoque (inicialmente desactivada; toggle con tecla 'l')
        self._magnifier_enabled: bool = False
        self._magnifier = MagnifierTool()
        # Modo sniper/precisión
        self._sniper = SniperModeManager()

        # Pantalla de inicio interna (landing): layout y widget contenedor
        self._main_layout = QtWidgets.QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._landing_widget = QtWidgets.QWidget(self)
        landing_layout = QtWidgets.QVBoxLayout(self._landing_widget)
        landing_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        landing_layout.setSpacing(12)
        landing_layout.setContentsMargins(24, 24, 24, 24)

        welcome = QtWidgets.QLabel('Bienvenido a <span style="color: #0E3468;">HICutter</span>')
        welcome.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        welcome_font = welcome.font()
        welcome_font.setPointSize(27)
        welcome_font.setBold(True)
        welcome.setFont(welcome_font)
        welcome.setStyleSheet('background-color: transparent')

        label = QtWidgets.QLabel('Selecciona la opcion de carga para iniciar el procesamiento')
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label_font = label.font()
        label_font.setPointSize(20)
        label_font.setBold(False)
        label.setFont(label_font)
        label.setStyleSheet('background-color: transparent')

        btn_batch = QtWidgets.QPushButton('Cargar Lote')
        btn_batch_font = btn_batch.font()
        btn_batch_font.setPointSize(16)
        btn_batch_font.setBold(False)
        btn_batch.setFont(btn_batch_font)
        btn_batch.setMinimumHeight(50)
        btn_batch.setFixedWidth(300)
        btn_batch.setStyleSheet('background-color: #252525; color: #EDEDED; border: 3px solid #0E3468; border-radius: 6px; padding: 8px;')

        btn_image = QtWidgets.QPushButton('Cargar Imagen')
        btn_image_font = btn_image.font()
        btn_image_font.setPointSize(16)
        btn_image_font.setBold(False)
        btn_image.setFont(btn_image_font)
        btn_image.setMinimumHeight(50)
        btn_image.setFixedWidth(300)
        btn_image.setStyleSheet('background-color: #252525; color: #EDEDED; border: 3px solid #0E3468; border-radius: 6px; padding: 8px;')
        btn_image.clicked.connect(lambda: self.requestLoadImage.emit())

        landing_layout.addStretch(1)
        landing_layout.addWidget(welcome)
        landing_layout.addSpacing(15)
        landing_layout.addWidget(label)
        landing_layout.addSpacing(70)
        landing_layout.addWidget(btn_image, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        landing_layout.addWidget(btn_batch, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        landing_layout.addStretch(1)

        self._main_layout.addWidget(self._landing_widget, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self._landing_widget.show()

        # Shortcut para alternar la lupa con la tecla 'L' (funciona aunque el widget no tenga foco)
        shortcut_l = QtGui.QShortcut(QtGui.QKeySequence('L'), self)
        shortcut_l.activated.connect(lambda: self._toggle_magnifier())

    def _toggle_magnifier(self) -> None:
        self._magnifier_enabled = not self._magnifier_enabled
        self.update()

    # ---------- Carga y conversión
    def load_image(self, path: Optional[str] = None, cv_image: Optional[np.ndarray] = None) -> None:
        """Carga una imagen desde `path` o desde un array OpenCV `cv_image` (BGR).
        Invoca update() para repintar el widget.
        """
        if path is None and cv_image is None:
            raise ValueError("Se requiere `path` o `cv_image`")

        if path is not None:
            img = cv2.imread(path)
            if img is None:
                raise IOError(f"No se pudo leer la imagen: {path}")
            self.cv_image = img
        else:
            # copiar para evitar aliasing accidental
            self.cv_image = cv_image.copy()

        self._pixmap = _cv_to_qpixmap(self.cv_image)
        # actualizar la referencia del manager
        self._scaled_manager.set_pixmap(self._pixmap)
        # ocultar pantalla de inicio al cargar imagen
        try:
            self._landing_widget.hide()
        except Exception:
            pass
        # actualizar caché escalado
        self._update_scaled_pixmap_cache()
        # reset points
        self._point_manager.reset()
        self.update()

    # Image conversion moved to `ui.utils._cv_to_qpixmap`

    def _create_cross_cursor(self, cross_len: int) -> QtGui.QCursor:
        """Crea un QCursor con una cruceta roja centrada."""
        size = cross_len * 2 + 7
        pix = QtGui.QPixmap(size, size)
        pix.fill(QtGui.QColor(0, 0, 0, 0))
        painter = QtGui.QPainter(pix)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        pen = QtGui.QPen(QtGui.QColor(220, 0, 0))
        pen.setWidth(1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        center = size // 2
        painter.drawLine(center - cross_len, center, center + cross_len, center)
        painter.drawLine(center, center - cross_len, center, center + cross_len)
        painter.end()
        return QtGui.QCursor(pix, center, center)


    # ---------- Utilidades de mapeo coordenadas
    def _scaled_pixmap_and_offset(self) -> Tuple[Optional[QtGui.QPixmap], int, int]:
        """Devuelve (scaled_pixmap, left, top) para centrar la imagen en el widget.
        Usa caché `self._scaled_pixmap_cache` actualizada sólo en load_image, rotate_cv y resizeEvent.
        """
        if self._pixmap is None:
            return None, 0, 0

        scaled, left, top = self._scaled_manager.get_scaled_and_offset()
        if scaled is None:
            self._update_scaled_pixmap_cache()
        return self._scaled_manager.get_scaled_and_offset()


    def _update_scaled_pixmap_cache(self) -> None:
        """Actualiza `self._scaled_pixmap_cache`, `left` y `top` en función
        del tamaño actual del widget y `self._pixmap`.
        Se debe llamar sólo en `load_image`, `rotate_cv` y `resizeEvent`.
        """
        # Delegate scaled-cache computation to the manager
        self._scaled_manager.set_pixmap(self._pixmap)
        self._scaled_manager.update_scaled_cache(self.size())

    def widget_to_image_coords(self, wx: int, wy: int) -> Optional[Tuple[float, float]]:
        """Convierte coordenadas de widget (px) a coordenadas en la imagen (px).
        Retorna None si el punto está fuera del área de la imagen (margen negro alrededor).
        """
        return self._scaled_manager.widget_to_image_coords(wx, wy)

    def image_to_widget_coords(self, ix: float, iy: float) -> Optional[Tuple[int, int]]:
        return self._scaled_manager.image_to_widget_coords(ix, iy)

    # ---------- Rotaciones (OpenCV)
    def rotate_cv(self, code: int) -> None:
        """Rota `self.cv_image` usando `cv2.rotate` con el código dado y actualiza la vista.
        Después de rotar se limpian los puntos seleccionados y se restaura el cursor.
        """
        if self.cv_image is None:
            return

        self.cv_image = cv2.rotate(self.cv_image, code)
        self._pixmap = _cv_to_qpixmap(self.cv_image)

        # actualizar caché escalado tras rotación
        self._update_scaled_pixmap_cache()
        # desactivar lupa al rotar
        self._magnifier_enabled = False
        # desactivar modo precisión si está activo y restaurar cursor
        self._sniper.deactivate(self)

        # limpiar puntos tras rotación
        self._point_manager.reset()

        # dejar de seguir el cursor y restaurar puntero
        self._mouse_in_img = False
        self.unsetCursor()

        self.update()

    def rotate_right(self) -> None:
        """Rotar 90° en sentido horario."""
        self.rotate_cv(cv2.ROTATE_90_CLOCKWISE)

    def rotate_left(self) -> None:
        """Rotar 90° en sentido antihorario."""
        self.rotate_cv(cv2.ROTATE_90_COUNTERCLOCKWISE)

    def rotate_180(self) -> None:
        """Rotar 180°."""
        self.rotate_cv(cv2.ROTATE_180)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        # Actualizar el pixmap escalado cuando cambia el tamaño del widget
        self._update_scaled_pixmap_cache()
        super().resizeEvent(event)
        self.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle keyboard shortcuts: 'l' toggles magnifier; Shift enters precision (sniper) mode.

        When Shift is pressed (non-autorepeat) we initialize the virtual cursor to the
        current mouse position, hide the system cursor and lock the system pointer to
        the widget center to allow infinite relative movement.
        """
        key = event.key()
        # Toggle magnifier
        if key == QtCore.Qt.Key.Key_L:
            self._magnifier_enabled = not self._magnifier_enabled
            self.update()
            return

        # Delegate sniper/precision handling
        handled, mwx, mwy = self._sniper.handle_key_press(event, self)
        if handled:
            if mwx is not None and mwy is not None:
                self._mouse_wx = mwx
                self._mouse_wy = mwy
            self.update()
            return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle Shift release to exit precision/sniper mode and restore cursor."""
        key = event.key()
        handled = self._sniper.handle_key_release(event, self)
        if handled:
            self.update()
            return
        super().keyReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Rastrea la posición del cursor y actualiza el cursor cuando está sobre la imagen.

        Si `self._precision_mode` está activo, se usa `_virtual_cursor_pos` y el
        movimiento físico se captura como delta relativo desde el centro del widget
        (bloqueando el cursor en el centro con `QCursor.setPos`).
        """
        # Delegate sniper precision movement
        handled, mwx, mwy, min_img = self._sniper.handle_mouse_move(event, self)
        if handled:
            # update canvas state from sniper
            if mwx is not None and mwy is not None:
                self._mouse_wx = mwx
                self._mouse_wy = mwy
            if isinstance(min_img, bool):
                self._mouse_in_img = min_img
            self.update()
            return

        # Comportamiento normal cuando no hay modo precisión
        wx = int(event.position().x())
        wy = int(event.position().y())
        img_pt = self.widget_to_image_coords(wx, wy)
        # Solo seguir el cursor si aún no se han colocado los 4 puntos
        if img_pt is not None and len(self._point_manager) < 4:
             self._mouse_in_img = True
             self._mouse_wx = wx
             self._mouse_wy = wy
             # cambiar cursor a cruceta roja
             self.setCursor(self._cross_cursor)
        else:
            if self._mouse_in_img:
                self._mouse_in_img = False
                self.unsetCursor()
        # repintar para mostrar líneas punteadas de referencia
        self.update()

    # ---------- Interacción de usuario
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            # Si estamos en modo precisión, usar la posición virtual (float) para mapear
            wfx, wfy = self._sniper.get_current_widget_pos(event, self)
            pt = self.widget_to_image_coords(wfx, wfy)
            if pt is None:
                return
            if len(self._point_manager) < 4:
                self._point_manager.add_point(pt)
                ordered = self._point_manager.finalize_if_full()
                # si alcanzamos 4 puntos, emitimos y dejamos de seguir el cursor
                if ordered is not None:
                    self.fourPointsSelected.emit(ordered)
                    # desactivar lupa y modo precisión al completar los 4 puntos
                    self._magnifier_enabled = False
                    self._sniper.deactivate(self)
                    self._mouse_in_img = False
                    self.unsetCursor()
                self.update()
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            # remove last
            if len(self._point_manager) > 0:
                self._point_manager.pop_last()
                # Si ahora hay menos de 4 puntos, el seguimiento volverá al moverse el mouse
                self.update()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        # doble click reinicia puntos
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._point_manager.reset()
            self.update()

    # ---------- Acceso a datos
    def get_points(self) -> np.ndarray:
        return self._point_manager.get_points()

    def reset_points(self) -> None:
        self._point_manager.reset()
        self.update()

    def unload_image(self) -> None:
        """Descarga la imagen actual y restaura el widget al estado inicial.
        - Limpia `self.cv_image`, `self._pixmap` y la caché escalada.
        - Limpia `self.points_img`, desactiva la lupa y el seguimiento del cursor.
        - Fuerza un repintado para mostrar el mensaje 'Carga una imagen'.
        """
        self.cv_image = None
        self._pixmap = None
        # reset manager cache
        # Reset scaled manager cache
        self._scaled_manager.set_pixmap(None)

        self._point_manager.reset()
        self._magnifier_enabled = False
        self._mouse_in_img = False
        self.unsetCursor()
        # mostrar la pantalla de inicio al descargar la imagen
        # mostrar la pantalla de inicio al descargar la imagen
        self._landing_widget.show()
        self.update()

    # Ordering logic moved to `PointManager` in ui/components/point_manager.py

    # ---------- Pintado
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(30, 30, 30))

        if self._pixmap is None:
            return

        scaled, left, top = self._scaled_pixmap_and_offset()
        assert scaled is not None
        painter.drawPixmap(left, top, scaled)
        # dibujar crucetas rojas finas (sin numeración)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        pen = QtGui.QPen(QtGui.QColor(220, 0, 0))
        pen.setWidth(1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        # líneas punteadas de referencia (conectan puntos y con el cursor)
        dash_pen = QtGui.QPen(QtGui.QColor(0, 0, 0))
        dash_pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        dash_pen.setWidth(1)
        dash_pen.setCosmetic(True)

        # Dibujar conexiones entre puntos (ordenadas)
        if len(self._point_manager) >= 2:
            painter.setPen(dash_pen)
            prev_w = None
            prev_h = None
            for (ix, iy) in self._point_manager.points:
                wcoords = self.image_to_widget_coords(ix, iy)
                if wcoords is None:
                    continue
                wx, wy = wcoords
                if prev_w is not None:
                    painter.drawLine(prev_w, prev_h, wx, wy)
                prev_w, prev_h = wx, wy
            # Efecto visual adicional cuando hay 4 puntos: conectar 1-3, 1-4 y 2-4
            if len(self._point_manager) == 4:
                w0 = self.image_to_widget_coords(*self._point_manager.points[0])
                w1 = self.image_to_widget_coords(*self._point_manager.points[1])
                w2 = self.image_to_widget_coords(*self._point_manager.points[2])
                w3 = self.image_to_widget_coords(*self._point_manager.points[3])
                if w0 is not None and w2 is not None:
                    painter.drawLine(w0[0], w0[1], w2[0], w2[1])
                if w0 is not None and w3 is not None:
                    painter.drawLine(w0[0], w0[1], w3[0], w3[1])
                if w1 is not None and w3 is not None:
                    painter.drawLine(w1[0], w1[1], w3[0], w3[1])

        # Si hay cursor sobre la imagen (y aún no se colocaron 4 puntos), dibujar líneas desde el cursor a cada punto
        if self._mouse_in_img and self._point_manager.points and len(self._point_manager) < 4:
            painter.setPen(dash_pen)
            for (ix, iy) in self._point_manager.points:
                wcoords = self.image_to_widget_coords(ix, iy)
                if wcoords is None:
                    continue
                wx, wy = wcoords
                painter.drawLine(wx, wy, self._mouse_wx, self._mouse_wy)

        # dibujar crucetas en cada punto
        painter.setPen(pen)
        for (ix, iy) in self._point_manager.points:
            wcoords = self.image_to_widget_coords(ix, iy)
            if wcoords is None:
                continue
            wx, wy = wcoords
            cl = self.cross_len
            painter.drawLine(wx - cl, wy, wx + cl, wy)
            painter.drawLine(wx, wy - cl, wx, wy + cl)

        # Lupa de enfoque: delegar en el MagnifierTool
        if self._magnifier_enabled and self._mouse_in_img and len(self._point_manager) < 4 and self.cv_image is not None:
            # obtener la posición de widget a usar (sniper virtual o real)
            wfx, wfy = self._sniper.get_current_widget_pos(None, self)
            img_pt = self.widget_to_image_coords(wfx, wfy)
            if img_pt is not None:
                # pasar posición widget en enteros para el overlay
                widget_pos = (int(round(wfx)), int(round(wfy)))
                # delegar dibujo a la herramienta
                self._magnifier.draw(painter, widget_pos, img_pt, self.cv_image, widget=self, cross_len=self.cross_len)

        painter.end()


if __name__ == "__main__":
    # pequeño sanity-check si se ejecuta como script
    import sys

    app = QtWidgets.QApplication(sys.argv)
    w = ImageCanvas()
    w.resize(800, 600)
    w.show()
    sys.exit(app.exec())
