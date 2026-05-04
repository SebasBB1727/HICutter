from PyQt6 import QtWidgets, QtGui, QtCore

class EditorToolbar(QtWidgets.QToolBar):
    """
    Componente visual independiente para la barra de herramientas del editor.
    Pricesa solo los botones y señales
    """
    # Generaremos señales que enviaran una peticion anuestro main
    sig_reset_requested = QtCore.pyqtSignal()
    sig_rotate_right_requested = QtCore.pyqtSignal()
    sig_rotate_left_requested = QtCore.pyqtSignal()
    sig_rotate_180_requested = QtCore.pyqtSignal()

    def __init__(self, parent = None) -> None:
        # Inicializamos la clase padre "toolbar" y le brindamos de apodo
        # "Herramientas de edicion"
        super().__init__("Herramientas de Edicion", parent)

        # llamamos a los metodos privados que brindan la estrucutra y personalizacion
        self._apply_style()
        self._setup_actions()

    def _apply_style(self) -> None:
        '''Aplica el diseño "css" a los botones'''
        #Inyectamos la hoja de estilos al componente padre
        self.setStyleSheet('''
        QToolButton {
            border: 1px solid #0E3468;
            background: transparent;
            padding: 4px 8px;
            border-radius: 4px;         
        }
        QToolButton:hover {
            background: rgba(37, 37, 37, 0.06);               
        }
        ''')
    
    def _setup_actions(self):
        '''Crea las acciones, brinda la estructura y 
        conecta las señales definidas al inicio de la clase'''

        # Boton "Reiniciar puntos"
        self.reset_action = QtGui.QAction('Reiniciar puntos', self)
        # Genera un recuadro flotante diciendo que hace este boton
        self.reset_action.setToolTip("Reinicia los todos los puntos colocados")
        self.reset_action.setShortcut("Esc")
        # Al presionar(.triggered), disparamos(.emit) nuestra señal
        self.reset_action.triggered.connect(self.sig_reset_requested.emit)
        self.addAction(self.reset_action)

        self.addSeparator() # <- Agrega una linea vertical, para dar estructura

        self.rotate_right_action = QtGui.QAction('Rotar 90° →', self)
        self.rotate_right_action.setToolTip("Rotar imagen 90° a la derecha")
        # Le asignamos atajos "Shortcuts" y un solo atajo "Shortcut"
        self.rotate_right_action.setShortcut("alt+1")
        self.rotate_right_action.triggered.connect(self.sig_rotate_right_requested.emit)
        self.addAction(self.rotate_right_action)

        self.rotate_left_action = QtGui.QAction('Rotar 90° ←', self)
        self.rotate_left_action.setToolTip("Rotar imagen 90° a la izquierda")
        self.rotate_left_action.triggered.connect(self.sig_rotate_left_requested.emit)
        self.addAction(self.rotate_left_action)

        self.rotate_180_action = QtGui.QAction('Rotar 180°', self)
        self.rotate_180_action.setToolTip("Rotar imagen 180°")
        self.rotate_180_action.triggered.connect(self.sig_rotate_180_requested.emit)
        self.addAction(self.rotate_180_action)

    def set_editor_active(self, is_active: bool) -> None:
        '''Metodo para encender/apagar la visalizacion y funcionalidad de la toolbar'''

        self.setVisible(is_active)
        self.setEnabled(is_active)