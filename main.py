# main.py

import sys
import ctypes
import os 
from PySide6.QtWidgets import QApplication, QStyle
from PySide6.QtGui import QIcon
from main_window import MainWindow

if __name__ == '__main__':
    # =====================================================================
    # === MODIFIED SECTION START (Set AppUserModelID for Windows) ===
    # =====================================================================
    # This is crucial for Windows to display the correct app name and icon
    # in notifications, especially when packaged with PyInstaller. It tells
    # the OS that our app is a distinct entity, not just a 'python' script.
    

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # =====================================================================
    # === MODIFIED SECTION START (Robust Icon Loading) ===
    # =====================================================================
    # Determine the base path for resources, which works for both development
    # and a packaged (frozen) application.
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.realpath(__file__))
    
    icon_path = os.path.join(base_path, "icon.ico")
    
    # Attempt to load the custom icon, with a fallback to a standard system icon.
    app_icon = QIcon(icon_path)
    if app_icon.isNull():
        style = app.style()
        app_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        
    app.setWindowIcon(app_icon)
    # =====================================================================
    # === MODIFIED SECTION END ===
    # =====================================================================
    
    main_win = MainWindow(app_icon=app_icon)
    main_win.show()
    
    sys.exit(app.exec())