# about_window.py

import os
import sys  # <--- ADDED IMPORT
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon

class AboutWindow(QDialog):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.version = version
        self.setWindowTitle("About Task Tracker")
        self.setFixedSize(350, 300) 
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # =====================================================================
        # === MODIFIED SECTION START (Robust path resolution for icon) ===
        # =====================================================================
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.realpath(__file__))

        # Change to load the .ico file, which can contain multiple sizes.
        icon_path = os.path.join(base_path, "icon.ico")
        # =====================================================================
        # === MODIFIED SECTION END ===
        # =====================================================================
        if os.path.exists(icon_path):
            icon_label = QLabel()
            
            # 1. Load the multi-image .ico file into a QIcon object.
            app_icon = QIcon(icon_path)
            
            # 2. Request a QPixmap of a specific size. QIcon will automatically
            #    select the best-matching image from the .ico file to generate it.
            pixmap = app_icon.pixmap(200, 200)
            icon_label.setPixmap(pixmap)
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