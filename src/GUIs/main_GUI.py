from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout

from src.GUIs.menus.menu_bar import MenuBar
from src.GUIs.widgets.tool_option_bar import ToolOptionBar
from src.GUIs.screens.workspace import WorkspaceScreen

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Main GUI")
        self.setGeometry(100, 100, 800, 600)

        # Set up the central widget and layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create and set the menu bar
        menu_bar = MenuBar(self)
        self.setMenuBar(menu_bar)

        # Create and add the central working space
        self.tool_option_bar = ToolOptionBar()
        self.workspace_screen = WorkspaceScreen(tool_option_bar=self.tool_option_bar)

        layout.addWidget(self.workspace_screen)
        layout.addWidget(self.tool_option_bar)