from PyQt6 import QtWidgets, QtGui, QtCore
import sys
import cv2
from core.processor import process_perspective_crop

from image_canvas import ImageCanvas
from ui.views.landing_view import LandingView


class MainWindow(QtWidgets.QMainWindow):
	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle('HICutter - Historical Image Cutter')

		# Stacked widget: 0 = LandingView, 1 = ImageCanvas (editor)
		self.stack = QtWidgets.QStackedWidget()
		self.landing = LandingView()
		self.canvas = ImageCanvas()
		self.stack.addWidget(self.landing)
		self.stack.addWidget(self.canvas)
		self.setCentralWidget(self.stack)
		self.current_image_path: str | None = None

		# Toolbar
		self.toolbar = self.addToolBar('main')
		# Aplicar estilo consistente a los botones del toolbar (borde #252525)
		self.toolbar.setStyleSheet("""
		QToolButton {
			border: 1px solid #0E3468;
			background: transparent;
			padding: 4px 8px;
			border-radius: 4px;
		}
		QToolButton:hover {
			background: rgba(37,37,37,0.06);
		}
		""")

		# Actions (kept as attributes to toggle visibility/state)
		self.reset_action = QtGui.QAction('Reiniciar puntos', self)
		self.reset_action.triggered.connect(self.canvas.reset_points)
		self.toolbar.addAction(self.reset_action)

		self.save_action = QtGui.QAction('Guardar puntos', self)
		self.save_action.triggered.connect(self.save_points)
		self.toolbar.addAction(self.save_action)

		self.canvas.fourPointsSelected.connect(self.on_four_points)

		# Botones de rotación (90° derecha, 90° izquierda, 180°)
		self.rotate_right_action = QtGui.QAction('Rotar 90° →', self)
		self.rotate_right_action.triggered.connect(self.canvas.rotate_right)
		self.toolbar.addAction(self.rotate_right_action)

		self.rotate_left_action = QtGui.QAction('Rotar 90° ←', self)
		self.rotate_left_action.triggered.connect(self.canvas.rotate_left)
		self.toolbar.addAction(self.rotate_left_action)

		self.rotate_180_action = QtGui.QAction('Rotar 180°', self)
		self.rotate_180_action.triggered.connect(self.canvas.rotate_180)
		self.toolbar.addAction(self.rotate_180_action)

		# Atajo Enter: guarda puntos si ya se tienen 4
		self.shortcut_return = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Return), self)
		self.shortcut_return.activated.connect(self._on_enter_key)
		self.shortcut_enter = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Enter), self)
		self.shortcut_enter.activated.connect(self._on_enter_key)

		# Atajos Alt+1 (rotar 90° derecha) y Alt+2 (guardar puntos cuando hay 4)
		self.shortcut_alt1 = QtGui.QShortcut(QtGui.QKeySequence('Alt+1'), self)
		self.shortcut_alt1.activated.connect(self.canvas.rotate_right)
		self.shortcut_alt2 = QtGui.QShortcut(QtGui.QKeySequence('Alt+2'), self)
		self.shortcut_alt2.activated.connect(self._on_enter_key)

		# Conectar la señal de la LandingView para abrir imagen
		try:
			self.landing.requestLoadImage.connect(self._handle_request_load_image)
		except Exception:
			# Si LandingView no tiene la señal, seguir sin error
			pass

		# Actualizar estado del toolbar cuando cambia la vista
		self.stack.currentChanged.connect(lambda idx: self.update_toolbar_state(idx == 1))
		# Mostrar la LandingView inicialmente
		self.stack.setCurrentIndex(0)
		self.update_toolbar_state(False)

	def load_image(self, path: str | None = None) -> None:
		# Si se proporciona `path`, úsalo; si no, abrir dialogo de archivo
		if path is None:
			fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Abrir imagen', 'input', 'Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)')
			if not fname:
				QtWidgets.QMessageBox.information(self, 'Aviso', 'No se selecciono ninguna carpeta')
				return
		else:
			fname = path
		img = cv2.imread(fname)
		if img is None:
			QtWidgets.QMessageBox.warning(self, 'Error', 'No se pudo cargar la imagen')
			return
		self.current_image_path = fname
		self.canvas.load_image(cv_image=img)
		# Cambiar a la vista del editor
		self.stack.setCurrentIndex(1)


	def on_four_points(self, pts) -> None:
		# pts es un numpy.ndarray shape (4,2) en coordenadas de la imagen (float32)
		print('4 puntos seleccionados (imagen coords):')
		print(pts)
		
	def _on_enter_key(self) -> None:
		# Ejecuta save_points si hay 4 puntos seleccionados
		pts = self.canvas.get_points()
		if pts.shape[0] == 4:
			self.save_points()

	def _handle_request_load_image(self, *args) -> None:
		# Wrapper that accepts optional path from LandingView signal
		path = args[0] if args else None
		self.load_image(path)

	def update_toolbar_state(self, editor_active: bool) -> None:
		# Mostrar/activar acciones y atajos solo cuando el editor está activo
		try:
			self.toolbar.setVisible(editor_active)
		except Exception:
			pass
		for a in (self.reset_action, self.save_action, self.rotate_right_action, self.rotate_left_action, self.rotate_180_action):
			a.setVisible(editor_active)
			a.setEnabled(editor_active)
		for s in (self.shortcut_return, self.shortcut_enter, self.shortcut_alt1, self.shortcut_alt2):
			s.setEnabled(editor_active)

	def save_points(self, path: str | None = None) -> None:
		"""Guardar puntos automáticamente en `CVFilesOutput` sin pedir nombre de archivo.
		Si `path` se proporciona, se usará esa ruta en su lugar.
		"""
		pts = self.canvas.get_points()
		if pts.shape[0] != 4:
			QtWidgets.QMessageBox.warning(self, 'Aviso', 'Faltan puntos (se requieren 4)')
			return
		import numpy as np
		import os
		import time

		if self.canvas.cv_image is None:
			QtWidgets.QMessageBox.warning(self, 'Error', 'No hay imagen cargada')
			return

		# puntos ordenados en coordenadas de la imagen (float32)
		src = pts.astype(np.float32)

		try:
			warped = process_perspective_crop(self.canvas.cv_image, src)
		except ValueError as e:
			QtWidgets.QMessageBox.warning(self, 'Error', str(e) if str(e) else 'Dimensiones inválidas para el recorte')
			return

		# guardar resultado en carpeta `output`
		os.makedirs('output', exist_ok=True)
		if path:
			out_fname = path
		else:
			# usar el nombre original si está disponible, sino usar timestamp
			base_name = None
			if getattr(self, 'current_image_path', None):
				base_name = os.path.basename(self.current_image_path)
			if base_name:
				out_fname = os.path.join('output', base_name)
			else:
				out_fname = os.path.join('output', f'crop_{time.strftime("%Y%m%d_%H%M%S")}.png')

		ok = cv2.imwrite(out_fname, warped)
		# Si el guardado fue correcto, descargar la imagen y limpiar la referencia
		if ok:
			try:
				self.canvas.unload_image()
			except Exception:
				pass
			self.current_image_path = None
			QtWidgets.QMessageBox.information(self, "Aviso", "Imagen guardada exitosamente")
			# Volver a la LandingView
			self.stack.setCurrentIndex(0)
		
		if not ok:
			QtWidgets.QMessageBox.warning(self, 'Error', f'No se pudo guardar la imagen en: {out_fname}')
			return


def main() -> None:
	app = QtWidgets.QApplication(sys.argv)
	mw = MainWindow()
	mw.resize(1000, 700)
	mw.show()
	sys.exit(app.exec())


if __name__ == '__main__':
	main()