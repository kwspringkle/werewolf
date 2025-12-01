from PyQt5 import QtWidgets, QtCore
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.image_utils import create_logo_label, set_window_icon


class WelcomeWindow(QtWidgets.QWidget):
    """Màn hình chào mừng, cho phép kết nối đến server và điều hướng đến đăng ký/đăng nhập"""
    
    def __init__(self, network_client, toast_manager, window_manager):
        super().__init__()
        self.network_client = network_client
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        
        self.setObjectName("welcome_window")
        self.setup_ui()
        
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        self.setWindowTitle("Werewolf - Welcome")
        self.resize(500, 500)
        
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addStretch()

        logo_label = create_logo_label(size=120)
        if logo_label:
            main_layout.addWidget(logo_label)
            main_layout.addSpacing(10)
        
        # Title
        title_label = QtWidgets.QLabel("🐺 WEREWOLF GAME")
        title_label.setObjectName("title_label")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        subtitle_label = QtWidgets.QLabel("One Night in the Village")
        subtitle_label.setObjectName("subtitle_label")
        subtitle_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(subtitle_label)
        
        main_layout.addSpacing(30)
        
        # Connection Group
        conn_group = QtWidgets.QGroupBox("Server Connection")
        conn_group.setObjectName("connection_group")
        conn_layout = QtWidgets.QFormLayout()

        # Thêm helper text
        help_label = QtWidgets.QLabel(
            "💡 For local: 127.0.0.1\n"
            "💡 For LAN: Use server's IP (e.g., 192.168.1.100)\n"
            "💡 Server must be running and port 5000 open"
        )
        help_label.setStyleSheet("color: #888; font-size: 10px;")
        
        self.host_input = QtWidgets.QLineEdit("127.0.0.1")
        self.host_input.setObjectName("host_input")
        self.port_input = QtWidgets.QLineEdit("5000")
        self.port_input.setObjectName("port_input")
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.setObjectName("connect_button")
        
        conn_layout.addRow(help_label)
        conn_layout.addRow("Host:", self.host_input)
        conn_layout.addRow("Port:", self.port_input)
        conn_layout.addRow("", self.connect_button)
        conn_group.setLayout(conn_layout)
        main_layout.addWidget(conn_group)
        
        main_layout.addSpacing(20)
        
        # Navigation buttons
        self.nav_group = QtWidgets.QWidget()
        nav_layout = QtWidgets.QHBoxLayout(self.nav_group)
        nav_layout.setContentsMargins(50, 0, 50, 0)
        nav_layout.setSpacing(20)
        
        self.register_button = QtWidgets.QPushButton("Register")
        self.register_button.setObjectName("register_button")
        self.register_button.setMinimumHeight(50)
        self.register_button.setEnabled(False)
        self.register_button.setStyleSheet("""
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
                border: 1px solid #444444;
            }
        """)
        
        self.login_button = QtWidgets.QPushButton("Login")
        self.login_button.setObjectName("login_button")
        self.login_button.setMinimumHeight(50)
        self.login_button.setEnabled(False)
        self.login_button.setStyleSheet("""
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
                border: 1px solid #444444;
            }
        """)
        
        nav_layout.addWidget(self.register_button)
        nav_layout.addWidget(self.login_button)
        
        main_layout.addWidget(self.nav_group)
        main_layout.addStretch()
        
        # Kết nối các tín hiệu
        self.connect_button.clicked.connect(self.on_connect)
        self.register_button.clicked.connect(self.on_register)
        self.login_button.clicked.connect(self.on_login)
        
    def on_connect(self):
        """Xử lý khi nhấn nút kết nối"""
        host = self.host_input.text().strip()
        port_text = self.port_input.text().strip()
        
        if not host or not port_text:
            self.toast_manager.warning("Please enter host and port")
            return
            
        try:
            port = int(port_text)
        except ValueError:
            self.toast_manager.error("Invalid port number")
            return
            
        try:
            self.network_client.create()
            self.network_client.connect(host, port)
            
            self.toast_manager.success(f"Connected to {host}:{port}")
            self.connect_button.setEnabled(False)
            self.host_input.setEnabled(False)
            self.port_input.setEnabled(False)
            
            # Enable navigation buttons
            self.register_button.setEnabled(True)
            self.register_button.setStyleSheet("")  # Reset to default style
            self.login_button.setEnabled(True)
            self.login_button.setStyleSheet("")  # Reset to default style
            
            # Store connection info
            self.window_manager.set_shared_data("network_client", self.network_client)
            self.window_manager.set_shared_data("connected", True)
            
        except Exception as e:
            self.toast_manager.error(f"Connection failed: {str(e)}")
            
    def on_register(self):
        """Điều hướng đến màn hình đăng ký"""
        self.window_manager.navigate_to("register")
        
    def on_login(self):
        """Điều hướng đến màn hình đăng nhập"""
        self.window_manager.navigate_to("login")
