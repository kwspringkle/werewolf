import sys
import socket
import json
from PyQt5 import QtWidgets, QtCore, QtGui


class ToastNotification(QtWidgets.QWidget):
    """
    Toast notification: hiển thị thông báo
    """
    
    def __init__(self, parent=None, message="", notification_type="info", duration=3000):
        super().__init__(parent, QtCore.Qt.ToolTip | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        
        self.message = message
        self.notification_type = notification_type
        self.duration = duration
        
        self.setup_ui()
        self.setup_animation()
        
    def setup_ui(self):
        """Setup the toast UI"""
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Icon
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.set_icon()
        
        # Message
        self.message_label = QtWidgets.QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("color: white; font-size: 13px;")
        
        # Close button
        self.close_button = QtWidgets.QPushButton("✕")
        self.close_button.setFixedSize(20, 20)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ff6b6b;
            }
        """)
        self.close_button.clicked.connect(self.fade_out)
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.message_label, 1)
        layout.addWidget(self.close_button)
        
        # Set background color dựa trên loại thông báo
        colors = {
            "info": "#3498db",
            "success": "#2ecc71",
            "warning": "#f39c12",
            "error": "#e74c3c"
        }
        bg_color = colors.get(self.notification_type, "#3498db")
        
        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: {bg_color};
                border-radius: 8px;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }}
        """)
        
        # Set fixed width
        self.setFixedWidth(350)
        self.adjustSize()
        
    def set_icon(self):
        """Set icon dựa theo loại thông báo"""
        icons = {
            "info": "ℹ️",
            "success": "✓",
            "warning": "⚠️",
            "error": "✗"
        }
        icon_text = icons.get(self.notification_type, "ℹ️")
        self.icon_label.setText(icon_text)
        self.icon_label.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_label.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        
    def setup_animation(self):
        """Hiệu ứng fade in/out"""
        # Opacity effect
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        # Hiệu ứng fade in
        self.fade_in_anim = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_anim.setDuration(300)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        
        # Hiệu ứng fade out
        self.fade_out_anim = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.fade_out_anim.finished.connect(self.close)
        
        # Auto-hide timer
        self.hide_timer = QtCore.QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)
        
    def show_notification(self):
        """Hiển thị thông báo"""
        self.show()
        self.fade_in_anim.start()
        self.hide_timer.start(self.duration)
        
    def fade_out(self):
        """Hiệu ứng fade out thông báo"""
        self.hide_timer.stop()
        self.fade_out_anim.start()


class ToastManager(QtCore.QObject):
    """
    Manager cho Toast Notifications
    Handles positioning và xếp chồng của nhiều thông báo
    """
    
    def __init__(self, parent_widget):
        super().__init__()
        self.parent_widget = parent_widget
        self.active_toasts = []
        self.spacing = 10
        
    def show_toast(self, message, notification_type="info", duration=3000):
        """Show a new toast notification"""
        toast = ToastNotification(
            parent=self.parent_widget,
            message=message,
            notification_type=notification_type,
            duration=duration
        )
        
        # Đặt vị trí cho toast
        self.position_toast(toast)
        
        # Thêm vào danh sách active
        self.active_toasts.append(toast)
        
        # Hiện thông báo
        toast.show_notification()
        
        # xóa toast khi đóng
        toast.destroyed.connect(lambda: self.remove_toast(toast))
        
        return toast
        
    def position_toast(self, toast):
        """Để toast ở bên phải, xếp chồng nếu có nhiều"""
        if not self.parent_widget:
            return
            
        parent_rect = self.parent_widget.geometry()
        
        # Tính vị trí - relative đến parent widget
        x = parent_rect.width() - toast.width() - 20
        y = 20
        
        # Xếp chồng các toast
        for existing_toast in self.active_toasts:
            if existing_toast.isVisible():
                y += existing_toast.height() + self.spacing
        
        # Vị trí trong parent widget
        toast.move(x, y)
        
    def remove_toast(self, toast):
        """Xóa toast khỏi danh sách active"""
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
            self.reposition_toasts()
            
    def reposition_toasts(self):
        """Đặt lại vị trí cho tất cả các toast đang hoạt động"""
        y = 20
        for toast in self.active_toasts:
            if toast.isVisible():
                parent_rect = self.parent_widget.geometry()
                x = parent_rect.width() - toast.width() - 20
                
                # Animate position change
                anim = QtCore.QPropertyAnimation(toast, b"pos")
                anim.setDuration(200)
                anim.setStartValue(toast.pos())
                anim.setEndValue(QtCore.QPoint(x, y))
                anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
                anim.start()
                
                y += toast.height() + self.spacing
                
    def info(self, message, duration=3000):
        """Hiển thị thông báo info"""
        return self.show_toast(message, "info", duration)
        
    def success(self, message, duration=3000):
        """Hiển thị thông báo success"""
        return self.show_toast(message, "success", duration)
        
    def warning(self, message, duration=4000):
        """Hiển thị thông báo warning"""
        return self.show_toast(message, "warning", duration)
        
    def error(self, message, duration=5000):
        """Hiển thị thông báo error"""
        return self.show_toast(message, "error", duration)