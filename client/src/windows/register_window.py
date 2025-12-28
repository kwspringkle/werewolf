from PyQt5 import QtWidgets, QtCore
import sys
from pathlib import Path

# Thêm utils vào đường dẫn
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.image_utils import create_logo_label


class RegisterWindow(QtWidgets.QWidget):
    """Cửa sổ đăng ký cho người dùng mới"""
    
    def __init__(self, toast_manager, window_manager):
        super().__init__()
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.network_client = None
        
        self.setObjectName("register_window")
        self.setup_ui()
        
        # Receive timer
        self.recv_timer = QtCore.QTimer()
        self.recv_timer.timeout.connect(self.receive_packets)
        
    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)
        # Get network client from shared data
        self.network_client = self.window_manager.get_shared_data("network_client")
        print(f"[DEBUG] Register window shown, network_client: {self.network_client}")
        if self.network_client:
            print("[DEBUG] Starting recv_timer for register window")
            self.recv_timer.start(100)
        else:
            print("[ERROR] No network_client available!")
        
        # Set focus to username input
        QtCore.QTimer.singleShot(100, lambda: self.username_input.setFocus())
        
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        self.setWindowTitle("Werewolf - Register")
        self.resize(500, 550)
        
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addStretch()

        logo_label = create_logo_label(size=100)
        if logo_label:
            main_layout.addWidget(logo_label)
            main_layout.addSpacing(10)
        
        # Title
        title_label = QtWidgets.QLabel("Create New Account")
        title_label.setObjectName("title_label")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        main_layout.addSpacing(20)
        
        # Register Group
        register_group = QtWidgets.QGroupBox("Registration")
        register_group.setObjectName("register_group")
        register_layout = QtWidgets.QFormLayout()
        
        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setObjectName("username_input")
        self.username_input.setPlaceholderText("Choose a username")
        
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setObjectName("password_input")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter password")
        
        self.confirm_password_input = QtWidgets.QLineEdit()
        self.confirm_password_input.setObjectName("confirm_password_input")
        self.confirm_password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm_password_input.setPlaceholderText("Confirm password")
        
        self.register_button = QtWidgets.QPushButton("Register")
        self.register_button.setObjectName("register_button")
        self.register_button.setMinimumHeight(40)
        
        register_layout.addRow("Username:", self.username_input)
        register_layout.addRow("Password:", self.password_input)
        register_layout.addRow("Confirm:", self.confirm_password_input)
        register_layout.addRow("", self.register_button)
        register_group.setLayout(register_layout)
        main_layout.addWidget(register_group)
        
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
        self.register_button.clicked.connect(self.on_register)
        self.back_button.clicked.connect(self.on_back)
        self.confirm_password_input.returnPressed.connect(self.on_register)
        
    def on_register(self):
        """Xử lý khi nhấn nút đăng ký"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        print(f"[DEBUG] Register clicked: username='{username}', password_len={len(password)}")
        
        if not username or not password:
            self.toast_manager.warning("Please enter username and password")
            return
            
        if len(username) < 3:
            self.toast_manager.warning("Username must be at least 3 characters")
            return
            
        if len(password) < 6:
            self.toast_manager.warning("Password must be at least 6 characters")
            return
            
        if password != confirm_password:
            self.toast_manager.error("Passwords do not match")
            return
        
        if not self.network_client:
            self.toast_manager.error("Not connected to server")
            print("[ERROR] network_client is None!")
            return
            
        try:
            payload = {"username": username, "password": password}
            print(f"[DEBUG] Sending REGISTER_REQ (103): {payload}")
            result = self.network_client.send_packet(103, payload)  # REGISTER_REQ
            print(f"[DEBUG] Send result: {result}")
            self.toast_manager.info("Registering...")
        except Exception as e:
            print(f"[ERROR] Register send failed: {e}")
            self.toast_manager.error(f"Failed to send registration: {str(e)}")
            
    def on_back(self):
        """Quay lại cửa sổ chào mừng"""
        self.recv_timer.stop()
        self.window_manager.navigate_to("welcome")
            
    def receive_packets(self):
        """Nhận gói tin từ server"""
        try:
            header, payload = self.network_client.receive_packet()
            
            if header is None:
                return  # No data
            
            print(f"[DEBUG] Register window received packet: header={header}, payload={payload}")
            self.handle_packet(header, payload)
            
        except RuntimeError as e:
            error_msg = str(e)
            print(f"[ERROR] Receive error in register window: {error_msg}")
            # Kiểm tra xem có phải server disconnect không
            if "Server closed" in error_msg or "Receive failed" in error_msg:
                print(f"[ERROR] Server disconnected: {error_msg}")
                self.handle_server_disconnect()
            else:
                self.toast_manager.error(f"Receive error: {error_msg}")
                self.recv_timer.stop()
        except Exception as e:
            print(f"[ERROR] Receive error in register window: {e}")
            self.toast_manager.error(f"Receive error: {str(e)}")
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
        print(f"[DEBUG] Register handle_packet: header={header}, payload={payload}")
        if header == 501:  # PING - Server gửi PING để kiểm tra connection
            try:
                self.network_client.send_packet(502, {"type": "pong"})  # 502 = PONG
            except Exception as e:
                print(f"[ERROR] Failed to send PONG: {e}")
        elif header == 502:  # PONG - Server trả về PONG (không cần xử lý)
            pass
        elif header == 104:  # REGISTER_RES
            if payload.get("status") == "success":
                # Lấy username từ input vì server không gửi lại
                username = self.username_input.text().strip()
                print(f"[SUCCESS] Registration successful for {username}")
                self.toast_manager.success(f"Account created! Welcome {username}")
                
                # Clear inputs
                self.username_input.clear()
                self.password_input.clear()
                self.confirm_password_input.clear()
                
                # Navigate to login
                self.recv_timer.stop()
                self.window_manager.navigate_to("login")
            else:
                msg = payload.get("message", "Unknown error")
                print(f"[ERROR] Registration failed: {msg}")
                self.toast_manager.error(f"Registration failed: {msg}")
        else:
            print(f"[WARNING] Unexpected packet in register window: {header}")
                
    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        self.recv_timer.stop()
        event.accept()
