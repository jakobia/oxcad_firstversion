"""
main.py - Entry point for CAD application

This file launches the main window and initializes the application.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from cadapp.gui.main_window import MainWindow
from cadapp.utils.logger import setup_logging


def main() -> None:
    """
    Main entry point for the CAD application.
    """
    setup_logging()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for cross-platform consistency

    # Enable dark mode
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.Base, QColor(20, 20, 20))
    dark_palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
    dark_palette.setColor(QPalette.ToolTipBase, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.Text, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.Button, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    app.setPalette(dark_palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
