from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
    QHBoxLayout, QComboBox, QMenu, QMessageBox
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QPoint, QPointF

from data.annotation_data_model import AnnotationModel, POINT_TYPES, AnnotationPoint

SELECT_RADIUS_PX = 8

class ImageAnnotationView(QWidget):
    def __init__(self, model: AnnotationModel, tool_option_bar: QWidget, parent=None):
        super().__init__(parent)
        self.model = model
        self.model.on_changed = self.update
        self.tool_option_bar = tool_option_bar

        self._pixmap_original: QPixmap | None = None
        self._selected_point_id: int | None = None
        self._pending_connection_start: int | None = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        tools = {
            "point_type": {
                "type": "combo_box",
                #"action": self.change_point_type,
                "options": POINT_TYPES
            },
            "load_image": {
                "type": "button",
                "action": self.load_image,
                "label": "Load Image"
            },
            "clear": {
                "type": "button",
                "action": self._clear_all,
                "label": "Clear"
            },
            "test": {
                "type": "button",
                "action": self._test_function,
                "label": "Test"
            },
        }
        self.tool_option_bar.set_tool_options(tools)

        self.type_combo = QComboBox()
        for key, (label, color) in POINT_TYPES.items():
            self.type_combo.addItem(f"{label}", userData=key)
        #top.addWidget(self.type_combo)
     

        self.image_label = QLabel(alignment=Qt.AlignCenter)
        self.image_label.setStyleSheet("background:#222; border:1px solid #444;")
        layout.addWidget(self.image_label, 1)

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        self._pixmap_original = QPixmap(path)
        if self._pixmap_original.isNull():
            QMessageBox.warning(self, "Load", "Failed to load image.")
            return
        self.model.clear()
        self._selected_point_id = None
        self._pending_connection_start = None
        #self.status_lbl.setText(f"Loaded: {path.split('/')[-1]}")
        self.update()

    def _clear_all(self):
        self.model.clear()
        self._selected_point_id = None
        self._pending_connection_start = None
        self.update()

    # ---------------- Interaction ---------------- #

    def mousePressEvent(self, event):
        if not self._pixmap_original:
            return

        if event.button() == Qt.LeftButton:
            img_pos = self._label_pos_to_image(event.pos())
            if not img_pos:
                return
            # Did we click an existing point?
            pt = self._find_point_near(img_pos, SELECT_RADIUS_PX)
            if pt:
                # Connection logic
                if self._pending_connection_start is None:
                    # Start a connection or select
                    self._pending_connection_start = pt.id
                    self._selected_point_id = pt.id
                    #self.status_lbl.setText(f"Selected point {pt.id}. Click another point to connect.")
                else:
                    if self._pending_connection_start != pt.id:
                        self.model.toggle_connection(self._pending_connection_start, pt.id)
                        #self.status_lbl.setText(
                        #    f"Toggled connection {self._pending_connection_start}-{pt.id}"
                        #)
                    self._pending_connection_start = None
                    self._selected_point_id = pt.id
            else:
                # Add new point
                type_key = self.type_combo.currentData()
                new_pt = self.model.add_point(img_pos, type_key)
                self._selected_point_id = new_pt.id
                self._pending_connection_start = None
                #self.status_lbl.setText(f"Added {POINT_TYPES[type_key][0]} #{new_pt.id}")
            self.update()

        elif event.button() == Qt.RightButton:
            img_pos = self._label_pos_to_image(event.pos())
            if not img_pos:
                return
            pt = self._find_point_near(img_pos, SELECT_RADIUS_PX)
            if pt:
                self._open_point_context_menu(pt, event.globalPos())

        super().mousePressEvent(event)

    def _open_point_context_menu(self, pt: AnnotationPoint, global_pos):
        menu = QMenu(self)
        sel_action = menu.addAction(f"Select #{pt.id}")
        del_action = menu.addAction(f"Delete #{pt.id}")
        action = menu.exec_(global_pos)
        if action == sel_action:
            self._selected_point_id = pt.id
            self._pending_connection_start = pt.id
            #self.status_lbl.setText(f"Selected point {pt.id}")
        elif action == del_action:
            self.model.remove_point(pt.id)
            if self._selected_point_id == pt.id:
                self._selected_point_id = None
            if self._pending_connection_start == pt.id:
                self._pending_connection_start = None
        self.update()

    # ---------------- Coordinate helpers ---------------- #

    def _label_pos_to_image(self, pos):
        """
        Convert a mouse position (in parent widget coords) to original image pixel coords.
        Returns (x_px, y_px) or None if outside the displayed image.
        """
        if not self._pixmap_original:
            return None

        # Translate from parent widget coords to label-local coords
        local = self.image_label.mapFrom(self, pos)

        # Work entirely in label local space (0,0 in top-left of label contents)
        label_rect = self.image_label.contentsRect()  # starts at (0,0)
        if not label_rect.contains(local):
            return None

        pix = self._pixmap_original
        # Scaled pixmap size for display (aspect ratio preserved)
        scaled = pix.scaled(label_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Centered placement offsets inside the label
        x_off = (label_rect.width() - scaled.width()) // 2
        y_off = (label_rect.height() - scaled.height()) // 2

        # Check inside the drawn scaled image
        if not (x_off <= local.x() <= x_off + scaled.width() and
                y_off <= local.y() <= y_off + scaled.height()):
            return None

        # Position relative to scaled image top-left
        rel_x = local.x() - x_off
        rel_y = local.y() - y_off

        # Scale back to original image pixel coordinates
        scale_x = pix.width() / scaled.width()
        scale_y = pix.height() / scaled.height()

        return int(rel_x * scale_x), int(rel_y * scale_y)

    def _find_point_near(self, pixel, radius):
        rx2 = radius * radius
        for p in self.model.points:
            dx = p.pixel[0] - pixel[0]
            dy = p.pixel[1] - pixel[1]
            if dx * dx + dy * dy <= rx2:
                return p
        return None

    # ---------------- Painting ---------------- #

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._pixmap_original:
            return

        base = self._pixmap_original.copy()
        painter = QPainter(base)

        # Draw connections first
        conn_pen = QPen(QColor("#cccccc"), 2)
        painter.setPen(conn_pen)
        for a_id, b_id in self.model.connections:
            a = self.model.find_point(a_id)
            b = self.model.find_point(b_id)
            if not a or not b:
                continue
            painter.drawLine(a.pixel[0], a.pixel[1], b.pixel[0], b.pixel[1])

        # Draw points
        for p in self.model.points:
            _, color = POINT_TYPES.get(p.type_key, ("?", "#ffffff"))
            pen = QPen(QColor(color), 8)
            painter.setPen(pen)
            painter.drawPoint(p.pixel[0], p.pixel[1])
            # Highlight selection
            if p.id == self._selected_point_id:
                sel_pen = QPen(QColor("#ffff00"), 2)
                painter.setPen(sel_pen)
                painter.drawEllipse(QPoint(p.pixel[0], p.pixel[1]), 10, 10)

        painter.end()

        # Scale to label
        label_rect = self.image_label.contentsRect()
        scaled = base.scaled(label_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)

    def _test_function(self):
        print("Test function called")
        print("Current points:")
        for p in self.model.points:
            print(f" - ID {p.id}: type {p.type_key}, pixel {p.pixel}")
        print("Current connections:")
        for a, b in self.model.connections:
            print(f" - {a} <-> {b}")

        
