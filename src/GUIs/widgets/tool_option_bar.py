from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from matplotlib.backend_bases import MouseButton

class ToolOptionBar(QWidget):
    def __init__(self, parent=None):
        super(ToolOptionBar, self).__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)
    
    def set_tool_options(self, options: dict):
        # Clear
        for i in reversed(range(self.layout().count())):
            widget = self.layout().itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        
        # Add
        for key, dict in options.items():
            if dict["type"] == "button":
                button = QPushButton(str(dict["label"]))
                button.clicked.connect(dict["action"])
                self.layout().addWidget(button)