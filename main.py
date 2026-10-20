#!/usr/bin/env python3
"""
VideoCut - Professional Video Editor
Entry point
"""

import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VideoCut")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("HenokDev")

    # Set default font
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    # Dark theme stylesheet
    app.setStyleSheet(DARK_STYLE)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


DARK_STYLE = """
QMainWindow {
    background-color: #1a1a1a;
    color: #ffffff;
}
QWidget {
    background-color: #1a1a1a;
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QMenuBar {
    background-color: #111111;
    color: #ffffff;
    border-bottom: 1px solid #333333;
    padding: 2px;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 12px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #333333;
}
QMenu {
    background-color: #222222;
    border: 1px solid #444444;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #fe2c55;
}
QMenu::separator {
    height: 1px;
    background: #444444;
    margin: 4px 8px;
}
QPushButton {
    background-color: #333333;
    color: #ffffff;
    border: none;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #444444;
}
QPushButton:pressed {
    background-color: #555555;
}
QPushButton#primaryBtn {
    background-color: #fe2c55;
    color: white;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #ff4060;
}
QPushButton#primaryBtn:pressed {
    background-color: #e0243d;
}
QPushButton#iconBtn {
    background-color: transparent;
    padding: 4px;
    border-radius: 4px;
}
QPushButton#iconBtn:hover {
    background-color: #333333;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #444444;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    background: #fe2c55;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider::sub-page:horizontal {
    background: #fe2c55;
    border-radius: 2px;
}
QSlider::groove:vertical {
    width: 4px;
    background: #444444;
    border-radius: 2px;
}
QSlider::handle:vertical {
    width: 14px;
    height: 14px;
    background: #fe2c55;
    border-radius: 7px;
    margin: 0 -5px;
}
QSlider::sub-page:vertical {
    background: #fe2c55;
    border-radius: 2px;
}
QLabel {
    color: #ffffff;
    background: transparent;
}
QLabel#sectionTitle {
    color: #aaaaaa;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QScrollBar:horizontal {
    height: 8px;
    background: #222222;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #555555;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #777777;
}
QScrollBar:vertical {
    width: 8px;
    background: #222222;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #555555;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #777777;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0; height: 0;
}
QSplitter::handle {
    background: #333333;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}
QToolTip {
    background-color: #333333;
    color: white;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}
QLineEdit {
    background-color: #333333;
    color: white;
    border: 1px solid #555555;
    border-radius: 6px;
    padding: 4px 8px;
}
QLineEdit:focus {
    border-color: #fe2c55;
}
QSpinBox, QDoubleSpinBox {
    background-color: #333333;
    color: white;
    border: 1px solid #555555;
    border-radius: 6px;
    padding: 4px 8px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #fe2c55;
}
QComboBox {
    background-color: #333333;
    color: white;
    border: 1px solid #555555;
    border-radius: 6px;
    padding: 4px 8px;
    min-width: 80px;
}
QComboBox:focus {
    border-color: #fe2c55;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #222222;
    color: white;
    border: 1px solid #444444;
    selection-background-color: #fe2c55;
}
QTabWidget::pane {
    border: none;
    background: #1a1a1a;
}
QTabBar::tab {
    background: #222222;
    color: #aaaaaa;
    padding: 8px 16px;
    border: none;
    border-radius: 0;
    font-size: 12px;
}
QTabBar::tab:selected {
    color: #ffffff;
    border-bottom: 2px solid #fe2c55;
    background: #1a1a1a;
}
QTabBar::tab:hover {
    color: #ffffff;
    background: #2a2a2a;
}
QProgressBar {
    background-color: #333333;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #fe2c55;
    border-radius: 4px;
}
QListWidget {
    background-color: #222222;
    border: none;
    border-radius: 6px;
    outline: none;
}
QListWidget::item {
    padding: 6px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #fe2c55;
    color: white;
}
QListWidget::item:hover {
    background-color: #333333;
}
QGroupBox {
    border: 1px solid #333333;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    color: #aaaaaa;
    font-size: 11px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QCheckBox {
    color: #ffffff;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 2px solid #555555;
    background: transparent;
}
QCheckBox::indicator:checked {
    background-color: #fe2c55;
    border-color: #fe2c55;
}
QRadioButton {
    color: #ffffff;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #555555;
}
QRadioButton::indicator:checked {
    background-color: #fe2c55;
    border-color: #fe2c55;
}
"""


if __name__ == "__main__":
    main()
