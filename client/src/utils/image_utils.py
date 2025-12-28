"""
Util cho hình ảnh trong ứng dụng Werewolf Client
"""

from PyQt5 import QtGui, QtWidgets, QtCore
from pathlib import Path


def get_image_path(filename):
    """Lấy ảnh từ thư mục assets/images"""
    images_dir = Path(__file__).parent.parent.parent / "assets" / "images"
    return images_dir / filename


def create_logo_label(size=150):
    """
    Tạo label logo từ file hình ảnh
    Trả về None nếu không tìm thấy hình ảnh
    """
    image_path = get_image_path("werewolf_logo.png")
    
    if image_path.exists():
        pixmap = QtGui.QPixmap(str(image_path))
        if not pixmap.isNull():
            logo_label = QtWidgets.QLabel()
            logo_label.setAlignment(QtCore.Qt.AlignCenter)
            scaled_pixmap = pixmap.scaled(
                size, size,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            logo_label.setPixmap(scaled_pixmap)
            return logo_label
    return None



def create_icon_label(emoji_char, size=48):
    """
    Tạo label icon từ emoji
    """
    icon_label = QtWidgets.QLabel()
    icon_label.setAlignment(QtCore.Qt.AlignCenter)
    icon_label.setText(emoji_char)
    font = QtGui.QFont()
    font.setFamily("Segoe UI Emoji, Apple Color Emoji, Noto Color Emoji, Arial")
    font.setPointSize(size // 2)
    icon_label.setFont(font)
    icon_label.setStyleSheet(f"font-size: {size}px;")
    return icon_label

def create_image_icon_label(image_filename, size=48):
    """
    Tạo label icon từ ảnh (png, jpg...)
    """
    image_path = get_image_path(image_filename)
    icon_label = QtWidgets.QLabel()
    icon_label.setAlignment(QtCore.Qt.AlignCenter)
    if image_path.exists():
        pixmap = QtGui.QPixmap(str(image_path))
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            icon_label.setPixmap(scaled_pixmap)
    return icon_label

def set_window_icon(window, icon_name="werewolf_icon.png"):
    """Set window icon"""
    icon_path = get_image_path(icon_name)
    
    if icon_path.exists():
        icon = QtGui.QIcon(str(icon_path))
        if not icon.isNull():
            window.setWindowIcon(icon)
            return True
    
    return False
