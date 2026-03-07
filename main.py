# main.py

import sys
import ctypes
import os 
import shutil
from PySide6.QtWidgets import QApplication, QStyle
from PySide6.QtGui import QIcon
from main_window import MainWindow


def ensure_resource_files():
    """Checks if bundled resource files exist in the EXE directory, and copies them if missing."""
    if not getattr(sys, 'frozen', False):
        return
        
    exe_dir = os.path.dirname(sys.executable)
    base_path = sys._MEIPASS
    files_to_copy = [
        'weekly_view.html', 'weekly_view.css', 'weekly_view.js',
        'report_template.html', 'report_template_six.html',
        'holiday.json', 'project_colors.json', 'project_names.json',
        'QA83.json', 'timesheet.json', 'travel.json',
        'config.json', 'icon.ico'
    ]
    
    for filename in files_to_copy:
        dest_path = os.path.join(exe_dir, filename)
        if not os.path.exists(dest_path):
            src_path = os.path.join(base_path, filename)
            if os.path.isfile(src_path):
                try:
                    shutil.copy2(src_path, dest_path)
                except Exception as e:
                    print(f"Error copying {filename}: {e}")

if __name__ == '__main__':
    ensure_resource_files()
    # =====================================================================
    # === MODIFIED SECTION START (Set AppUserModelID for Windows) ===
    # =====================================================================
    # This is crucial for Windows to display the correct app name and icon
    # in notifications, especially when packaged with PyInstaller. It tells
    # the OS that our app is a distinct entity, not just a 'python' script.
    

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Global stylesheet to fix UI issues
    app.setStyleSheet("""
        QCalendarWidget {
            min-width: 300px;
        }
        QCalendarWidget QToolButton {
            padding-right: 20px;
        }
        QCalendarWidget QToolButton#qt_calendar_monthbutton {
            min-width: 120px;
        }
        QCalendarWidget QToolButton#qt_calendar_yearbutton {
            min-width: 70px;
        }
    """)
    
    # =====================================================================
    # === MODIFIED SECTION START (Robust Icon Loading) ===
    # =====================================================================
    # Determine the base path for resources, which works for both development
    # and a packaged (frozen) application.
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
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