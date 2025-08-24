# about_window.py

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

class AboutWindow(QDialog):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.version = version
        self.setWindowTitle("About Task Tracker")
        self.setFixedSize(350, 300) 
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        script_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(script_dir, "icon.png")
        if os.path.exists(icon_path):
            icon_label = QLabel()
            pixmap = QPixmap(icon_path)
            # =====================================================================
            # === MODIFIED SECTION START (Force high-quality smooth scaling) ===
            # =====================================================================
            # Even if the image is 150x150, using .scaled() with SmoothTransformation
            # forces Qt to apply an anti-aliasing filter, which will smooth out
            # any jagged edges present in the source image file itself.
            icon_label.setPixmap(pixmap.scaled(
                150, 150, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation # This is the crucial part
            ))
            # =====================================================================
            # === MODIFIED SECTION END ===
            # =====================================================================
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon_label)
        
        about_text = f"""
        <center>
            <h3>Task Tracker</h3>
            <p>Version {self.version}</p>
            <p>A simple application to track time and tasks.</p>
            <p><b>Author:</b> Lai Shi Jian</p>
            <hr>
            <p><b>Libraries Used:</b><br>
            PySide6 (GUI Framework)<br>
            sqlite3 (Database)</p>
        </center>
        """
        
        content_label = QLabel(about_text)
        content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_label.setWordWrap(True)
        layout.addWidget(content_label)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addStretch()
        layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignCenter)