from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget
from data.annotation_data_model import AnnotationModel
from src.GUIs.screens.annotation_view import ImageAnnotationView
from src.GUIs.screens.coordinate_view import CoordinateView


class WorkspaceScreen(QWidget):
    def __init__(self, tool_option_bar: QWidget):
        super().__init__()
        self.tool_option_bar = tool_option_bar

        self.model = AnnotationModel()        
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        # Mode buttons (could also move to ToolOptionBar)
        mode_row = QHBoxLayout()
        self.img_mode_btn = QPushButton("Image Mode")
        self.coord_mode_btn = QPushButton("Coordinate Mode")
        self.img_mode_btn.clicked.connect(lambda: self.set_mode(0))
        self.coord_mode_btn.clicked.connect(lambda: self.set_mode(1))
        mode_row.addWidget(self.img_mode_btn)
        mode_row.addWidget(self.coord_mode_btn)
        outer.addLayout(mode_row)

        self.stack = QStackedWidget()
        self.image_view = ImageAnnotationView(self.model, tool_option_bar=self.tool_option_bar)
        self.coord_view = CoordinateView(self.model, tool_option_bar=self.tool_option_bar)
        self.stack.addWidget(self.image_view)
        self.stack.addWidget(self.coord_view)
        outer.addWidget(self.stack, 1)

        self.set_mode(0)

    def set_mode(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self.update_mode_buttons()

    def update_mode_buttons(self):
        idx = self.stack.currentIndex()
        self.img_mode_btn.setEnabled(idx != 0)
        self.coord_mode_btn.setEnabled(idx != 1)