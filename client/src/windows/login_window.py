from PyQt5 import QtWidgets, QtCore
import sys
from pathlib import Path

# Thêm utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.image_utils import create_logo_label
from utils.connection_monitor import ConnectionMonitor


class LoginWindow(QtWidgets.QWidget):
    """Cửa sổ đăng nhập cho người dùng đã có tài khoản"""
    
    def __init__(self, toast_manager, window_manager):
        super().__init__()
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.network_client = None

        self.setObjectName("login_window")
        self.setup_ui()

        # Receive timer
        self.recv_timer = QtCore.QTimer()
        self.recv_timer.timeout.connect(self.receive_packets)

        # Connection monitor
        self.connection_monitor = None
        
    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)
        # Lấy client mạng từ dữ liệu chia sẻ
        self.network_client = self.window_manager.get_shared_data("network_client")
        if self.network_client:
            self.recv_timer.start(100)

        # Set focus to username input
        QtCore.QTimer.singleShot(100, lambda: self.username_input.setFocus())

        # Setup connection monitor
        if not self.connection_monitor and self.network_client:
            self.connection_monitor = ConnectionMonitor(
                self.network_client,
                self.toast_manager,
                self.window_manager
            )
            self.connection_monitor.connection_lost.connect(self.on_connection_lost)
            self.connection_monitor.connection_restored.connect(self.on_connection_restored)
        if self.connection_monitor:
            self.connection_monitor.start()
        
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        self.setWindowTitle("Werewolf - Login")
        self.resize(500, 500)
        
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addStretch()

        logo_label = create_logo_label(size=100)
        if logo_label:
            main_layout.addWidget(logo_label)
            main_layout.addSpacing(10)
        
        # Title
        title_label = QtWidgets.QLabel("Login to Your Account")
        title_label.setObjectName("title_label")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        main_layout.addSpacing(20)
        
        # Login Group
        login_group = QtWidgets.QGroupBox("Login")
        login_group.setObjectName("login_group")
        login_layout = QtWidgets.QFormLayout()
        
        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setObjectName("username_input")
        self.username_input.setPlaceholderText("Enter username")
        
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setObjectName("password_input")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter password")
        
        self.login_button = QtWidgets.QPushButton("Login")
        self.login_button.setObjectName("login_button")
        self.login_button.setMinimumHeight(40)
        
        login_layout.addRow("Username:", self.username_input)
        login_layout.addRow("Password:", self.password_input)
        login_layout.addRow("", self.login_button)
        login_group.setLayout(login_layout)
        main_layout.addWidget(login_group)
        
        main_layout.addSpacing(10)
        
        # Back button
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        self.back_button = QtWidgets.QPushButton("← Back")
        self.back_button.setObjectName("back_button")
        button_layout.addWidget(self.back_button)
        
        main_layout.addLayout(button_layout)
        main_layout.addStretch()
        
        # Kết nối các tín hiệu
        self.login_button.clicked.connect(self.on_login)
        self.back_button.clicked.connect(self.on_back)
        self.password_input.returnPressed.connect(self.on_login)
        
    def hideEvent(self, event):
        """Called when window is hidden"""
        super().hideEvent(event)
        self.recv_timer.stop()
        if self.connection_monitor:
            self.connection_monitor.stop()

    def on_back(self):
        """Quay lại cửa sổ chào mừng"""
        self.window_manager.navigate_to("welcome")
            
    def on_login(self):
        """Xử lý khi nhấn nút đăng nhập"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            self.toast_manager.warning("Please enter username and password")
            return
            
        try:
            payload = {"username": username, "password": password}
            self.network_client.send_packet(101, payload)  # LOGIN_REQ
            self.toast_manager.info("Logging in...")
        except Exception as e:
            self.toast_manager.error(f"Failed to send login: {str(e)}")
            
    def receive_packets(self):
        """Nhận gói tin từ server"""
        try:
            header, payload = self.network_client.receive_packet()

            if header is None:
                return  # No data
            
            self.handle_packet(header, payload)
            
        except RuntimeError as e:
            error_msg = str(e)
            # Kiểm tra xem có phải server disconnect không
            if "Server closed" in error_msg or "Receive failed" in error_msg:
                print(f"[ERROR] Server disconnected: {error_msg}")
                self.handle_server_disconnect()
            else:
                self.toast_manager.error(f"Receive error: {error_msg}")
                self.recv_timer.stop()
        except ConnectionError as e:
            # Connection lost detected
            print(f"[DEBUG] Connection lost: {e}")
            self.recv_timer.stop()

            # Trigger connection lost handling via monitor
            if self.connection_monitor:
                self.connection_monitor.is_connected = False
                self.connection_monitor.stop()
                self.connection_monitor.handle_connection_lost()
        except Exception as e:
            # Other errors
            error_msg = str(e)
            print(f"[DEBUG] Other error: {error_msg}")
            self.toast_manager.error(f"Receive error: {error_msg}")
            self.recv_timer.stop()
            
    def handle_server_disconnect(self):
        """Xử lý khi server disconnect"""
        print("[DEBUG] Handling server disconnect...")
        # Dừng receive timer
        self.recv_timer.stop()
        
        # Hiển thị thông báo
        self.toast_manager.error("⚠️ Server disconnected! Returning to welcome screen...")
        
        # Cleanup network client
        try:
            if self.network_client:
                self.network_client.disconnect()
                self.network_client.destroy()
        except Exception as e:
            print(f"[ERROR] Error during cleanup: {e}")
        
        # Clear shared data
        self.window_manager.set_shared_data("network_client", None)
        
        # Navigate về welcome screen
        self.window_manager.navigate_to("welcome")
            
    def handle_packet(self, header, payload):
        """Xử lý gói tin nhận được"""
        # Handle PING from server
        if header == 501:  # PING
            try:
                self.network_client.send_packet(502, {"type": "pong"})  # 502 = PONG
                if self.connection_monitor:
                    self.connection_monitor.on_pong_received()
            except Exception as e:
                print(f"[ERROR] Failed to send PONG: {e}")
            return
        elif header == 502:  # PONG - Server trả về PONG (không cần xử lý)
            pass
        elif header == 102:  # LOGIN_RES
            if payload.get("status") == "success":
                user_id = payload.get("user_id")
                username = payload.get("username")
                
                self.toast_manager.success(f"Welcome back, {username}!")
                
                # Store user data
                self.window_manager.set_shared_data("user_id", user_id)
                self.window_manager.set_shared_data("username", username)
                
                # Stop receiving here
                self.recv_timer.stop()
                
                # Navigate to lobby
                self.window_manager.navigate_to("lobby")
            else:
                msg = payload.get("message", "Unknown error")
                self.toast_manager.error(f"Login failed: {msg}")

    def on_connection_lost(self):
        """Handle connection lost"""
        self.recv_timer.stop()

    def on_connection_restored(self):
        """Handle connection restored after reconnect"""
        print("[DEBUG] Login: Connection restored, restarting timer")
        # Restart timer
        if not self.recv_timer.isActive():
            self.recv_timer.start(100)

    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        self.recv_timer.stop()
        if self.connection_monitor:
            self.connection_monitor.stop()
        event.accept()
