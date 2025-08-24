# main.py

import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # To prevent the app from closing when the last window is closed
    app.setQuitOnLastWindowClosed(False)
    
    main_win = MainWindow()
    main_win.show()
    
    sys.exit(app.exec())