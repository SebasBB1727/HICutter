from PyQt6 import QtWidgets, QtGui, QtCore
import sys
import cv2
from core.processor import process_perspective_crop

from image_canvas import ImageCanvas


class MainWindow(QtWidgets.QMainWindow):
	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle('HICutter - Historical Image Cutter')
		self.canvas = ImageCanvas()
		self.setCentralWidget(self.canvas)
		self.current_image_path: str | None = None

		toolbar = self.addToolBar('main')
		# Aplicar estilo consistente a los botones del toolbar (borde #252525)
		toolbar.setStyleSheet("""
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

		reset_action = QtGui.QAction('Reiniciar puntos', self)
		reset_action.triggered.connect(self.canvas.reset_points)
		toolbar.addAction(reset_action)

		save_action = QtGui.QAction('Guardar puntos', self)
		save_action.triggered.connect(self.save_points)
		toolbar.addAction(save_action)

		self.canvas.fourPointsSelected.connect(self.on_four_points)
		self.canvas.requestLoadImage.connect(self.load_image)

		# Botones de rotación (90° derecha, 90° izquierda, 180°)
		rotate_right_action = QtGui.QAction('Rotar 90° →', self)
		rotate_right_action.triggered.connect(self.canvas.rotate_right)
		toolbar.addAction(rotate_right_action)

		rotate_left_action = QtGui.QAction('Rotar 90° ←', self)
		rotate_left_action.triggered.connect(self.canvas.rotate_left)
		toolbar.addAction(rotate_left_action)

		rotate_180_action = QtGui.QAction('Rotar 180°', self)
		rotate_180_action.triggered.connect(self.canvas.rotate_180)
		toolbar.addAction(rotate_180_action)

		# Atajo Enter: guarda puntos si ya se tienen 4
		shortcut_return = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Return), self)
		shortcut_return.activated.connect(self._on_enter_key)
		shortcut_enter = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Enter), self)
		shortcut_enter.activated.connect(self._on_enter_key)

		# Atajos Alt+1 (rotar 90° derecha) y Alt+2 (guardar puntos cuando hay 4)
		shortcut_alt1 = QtGui.QShortcut(QtGui.QKeySequence('Alt+1'), self)
		shortcut_alt1.activated.connect(self.canvas.rotate_right)
		shortcut_alt2 = QtGui.QShortcut(QtGui.QKeySequence('Alt+2'), self)
		shortcut_alt2.activated.connect(self._on_enter_key)

	def load_image(self) -> None:
		fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Abrir imagen', 'input', 'Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)')
		if not fname:
			QtWidgets.QMessageBox.information(self, 'Aviso', 'No se selecciono ninguna carpeta')
			return
		img = cv2.imread(fname)
		if img is None:
			QtWidgets.QMessageBox.warning(self, 'Error', 'No se pudo cargar la imagen')
			return
		self.current_image_path = fname
		self.canvas.load_image(cv_image=img)


	def on_four_points(self, pts) -> None:
		# pts es un numpy.ndarray shape (4,2) en coordenadas de la imagen (float32)
		print('4 puntos seleccionados (imagen coords):')
		print(pts)
		
	def _on_enter_key(self) -> None:
		# Ejecuta save_points si hay 4 puntos seleccionados
		pts = self.canvas.get_points()
		if pts.shape[0] == 4:
			self.save_points()

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