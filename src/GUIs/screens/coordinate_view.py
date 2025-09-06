from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from data.annotation_data_model import AnnotationModel

from pyvistaqt import QtInteractor
import pyvista as pv


class CoordinateView(QWidget):
    def __init__(self, model: AnnotationModel, tool_option_bar: QWidget, parent=None):
        super().__init__(parent)
        self.model = model
        self.model.on_changed = self.refresh
        layout = QVBoxLayout(self)
        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor)
        self.plotter.add_axes()
        self.refresh()

    def refresh(self):
        pass
        #if not hasattr(self, "plotter") or self.plotter is None:
        #    return
        #self.plotter.clear()
        #pts = []
        #for p in self.model.points:
        #    if p.world:
        #        pts.append([p.world[0], p.world[1], 0.0])
        #if pts:
        #    cloud = pv.PolyData(pts)
        #    self.plotter.add_points(cloud, color="red", point_size=12)
        #    # Optionally connect points:
        #    if len(pts) > 1:
        #        lines = []
        #        for i in range(len(pts)-1):
        #            lines.extend([2, i, i+1])
        #        poly = pv.PolyData()
        #        poly.points = pts
        #        poly.lines = lines
        #        self.plotter.add_mesh(poly, color="white")
        #self.plotter.reset_camera()
        #self.plotter.update()