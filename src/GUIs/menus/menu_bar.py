from PyQt5.QtWidgets import QMenuBar, QAction

class MenuBar(QMenuBar):
    def __init__(self, parent=None):
        super(MenuBar, self).__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Create the "Datei" menu
        datei_menu = self.addMenu("Datei")
        # Add actions to the "Datei" menu
        datei_menu.addAction(QAction("Öffnen", self))
        datei_menu.addAction(QAction("Speichern", self))
        datei_menu.addAction(QAction("Beenden", self))

        # Create the "Bearbeiten" menu
        bearbeiten_menu = self.addMenu("Bearbeiten")
        # Add actions to the "Bearbeiten" menu
        bearbeiten_menu.addAction(QAction("Rückgängig", self))
        bearbeiten_menu.addAction(QAction("Wiederherstellen", self))

        # Create the "Ansicht" menu
        ansicht_menu = self.addMenu("Ansicht")
        # Add actions to the "Ansicht" menu
        ansicht_menu.addAction(QAction("Toolleiste einblenden", self))
        ansicht_menu.addAction(QAction("Toolleiste ausblenden", self))
