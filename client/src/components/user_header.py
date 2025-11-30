from PyQt5 import QtWidgets, QtCore, QtGui


class UserHeader(QtWidgets.QWidget):
    """Header trong các trang sau khi đăng nhập, hiển thị username và menu logout"""
    
    logout_clicked = QtCore.pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = ""
        self.setup_ui()
        
    def setup_ui(self):
        """Thiết lập giao diện"""
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # User button with username
        self.user_button = QtWidgets.QPushButton()
        self.user_button.setObjectName("user_button")
        self.user_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.user_button.setFlat(True)
        self.user_button.setStyleSheet("""
            QPushButton#user_button {
                background-color: transparent;
                border: 2px solid #3498db;
                border-radius: 20px;
                padding: 8px 16px;
                font-weight: bold;
                color: #3498db;
            }
            QPushButton#user_button:hover {
                background-color: #3498db;
                color: white;
            }
        """)
        
        # Tạo menu
        self.menu = QtWidgets.QMenu(self)
        self.menu.setObjectName("user_menu")
        
        logout_action = QtWidgets.QAction("🚪 Logout", self)
        logout_action.triggered.connect(self.on_logout)
        self.menu.addAction(logout_action)
        
        # Kết nối nút để hiển thị menu
        self.user_button.clicked.connect(self.show_menu)
        
        layout.addStretch()
        layout.addWidget(self.user_button)
        
    def set_username(self, username):
        """Đặt username để hiển thị"""
        self.username = username
        self.user_button.setText(f"👤 {username}")
        
    def show_menu(self):
        """Hiển thị menu dropdown"""
        # Position menu below button
        pos = self.user_button.mapToGlobal(QtCore.QPoint(0, self.user_button.height()))
        self.menu.exec_(pos)
        
    def on_logout(self):
        """Phát tín hiệu logout"""
        self.logout_clicked.emit()
