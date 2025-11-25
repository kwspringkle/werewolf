import sys
import socket
import json
from PyQt5 import QtWidgets, QtCore

class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.sock = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Werewolf Game - Login")
        self.resize(400, 500)

        # Log area
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)

        # Connection section
        conn_group = QtWidgets.QGroupBox("Connection")
        conn_layout = QtWidgets.QHBoxLayout()

        self.host_input = QtWidgets.QLineEdit("127.0.0.1")
        self.port_input = QtWidgets.QLineEdit("5000")
        self.port_input.setMaximumWidth(80)
        self.btn_connect = QtWidgets.QPushButton("Connect")

        conn_layout.addWidget(QtWidgets.QLabel("Host:"))
        conn_layout.addWidget(self.host_input)
        conn_layout.addWidget(QtWidgets.QLabel("Port:"))
        conn_layout.addWidget(self.port_input)
        conn_layout.addWidget(self.btn_connect)
        conn_group.setLayout(conn_layout)

        # Login section
        login_group = QtWidgets.QGroupBox("Login")
        login_layout = QtWidgets.QFormLayout()

        self.login_username = QtWidgets.QLineEdit()
        self.login_password = QtWidgets.QLineEdit()
        self.login_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.btn_login = QtWidgets.QPushButton("Login")
        self.btn_login.setEnabled(False)

        login_layout.addRow("Username:", self.login_username)
        login_layout.addRow("Password:", self.login_password)
        login_layout.addRow(self.btn_login)
        login_group.setLayout(login_layout)

        # Register section
        register_group = QtWidgets.QGroupBox("Register")
        register_layout = QtWidgets.QFormLayout()

        self.register_username = QtWidgets.QLineEdit()
        self.register_password = QtWidgets.QLineEdit()
        self.register_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.register_password2 = QtWidgets.QLineEdit()
        self.register_password2.setEchoMode(QtWidgets.QLineEdit.Password)
        self.btn_register = QtWidgets.QPushButton("Register")
        self.btn_register.setEnabled(False)

        register_layout.addRow("Username:", self.register_username)
        register_layout.addRow("Password:", self.register_password)
        register_layout.addRow("Confirm:", self.register_password2)
        register_layout.addRow(self.btn_register)
        register_group.setLayout(register_layout)

        # Main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(conn_group)
        main_layout.addWidget(login_group)
        main_layout.addWidget(register_group)
        main_layout.addWidget(QtWidgets.QLabel("Log:"))
        main_layout.addWidget(self.log)
        self.setLayout(main_layout)

        # Connect signals
        self.btn_connect.clicked.connect(self.connect_server)
        self.btn_login.clicked.connect(self.do_login)
        self.btn_register.clicked.connect(self.do_register)

        # Receive timer
        self.recv_timer = QtCore.QTimer()
        self.recv_timer.timeout.connect(self.receive_packet)

    def connect_server(self):
        try:
            host = self.host_input.text()
            port = int(self.port_input.text())

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.sock.setblocking(False)

            self.log.append(f"✓ Connected to {host}:{port}")

            self.btn_connect.setEnabled(False)
            self.btn_login.setEnabled(True)
            self.btn_register.setEnabled(True)

            self.recv_timer.start(100)

        except Exception as e:
            self.log.append(f"✗ Connection failed: {e}")

    def send_packet(self, header, payload_dict):
        if not self.sock:
            self.log.append("✗ Not connected to server")
            return

        try:
            payload_json = json.dumps(payload_dict)
            payload_bytes = payload_json.encode('utf-8')

            packet = (
                header.to_bytes(2, "big") +
                len(payload_bytes).to_bytes(4, "big") +
                payload_bytes
            )

            self.sock.sendall(packet)
            self.log.append(f"→ Sent header={header}: {payload_json}")

        except Exception as e:
            self.log.append(f"✗ Send error: {e}")

    def do_login(self):
        username = self.login_username.text().strip()
        password = self.login_password.text()

        if not username or not password:
            self.log.append("✗ Please enter username and password")
            return

        payload = {
            "username": username,
            "password": password
        }

        self.send_packet(101, payload)  # LOGIN_REQ = 101

    def do_register(self):
        username = self.register_username.text().strip()
        password = self.register_password.text()
        password2 = self.register_password2.text()

        if not username or not password:
            self.log.append("✗ Please enter username and password")
            return

        if password != password2:
            self.log.append("✗ Passwords do not match")
            return

        payload = {
            "username": username,
            "password": password
        }

        self.send_packet(103, payload)  # REGISTER_REQ = 103

    def receive_packet(self):
        try:
            # Try to read header (2 bytes)
            header_bytes = self.sock.recv(2)
            if not header_bytes or len(header_bytes) < 2:
                return

            header = int.from_bytes(header_bytes, "big")

            # Read length (4 bytes)
            length_bytes = self.sock.recv(4)
            if len(length_bytes) < 4:
                return

            length = int.from_bytes(length_bytes, "big")

            # Read payload
            payload_bytes = b""
            while len(payload_bytes) < length:
                chunk = self.sock.recv(length - len(payload_bytes))
                if not chunk:
                    break
                payload_bytes += chunk

            payload_str = payload_bytes.decode('utf-8')

            # Parse response
            self.handle_response(header, payload_str)

        except BlockingIOError:
            pass
        except Exception as e:
            self.log.append(f"✗ Receive error: {e}")

    def handle_response(self, header, payload_str):
        try:
            data = json.loads(payload_str)

            if header == 102:  # LOGIN_RES
                self.log.append(f"← LOGIN RESPONSE:")
                if data.get("status") == "success":
                    user_id = data.get("user_id")
                    self.log.append(f"   ✓ Login successful! User ID: {user_id}")
                else:
                    msg = data.get("message", "Unknown error")
                    self.log.append(f"   ✗ Login failed: {msg}")

            elif header == 104:  # REGISTER_RES
                self.log.append(f"← REGISTER RESPONSE:")
                if data.get("status") == "success":
                    self.log.append(f"   ✓ Registration successful!")
                else:
                    msg = data.get("message", "Unknown error")
                    self.log.append(f"   ✗ Registration failed: {msg}")
            else:
                self.log.append(f"← Received header={header}: {payload_str}")

        except json.JSONDecodeError:
            self.log.append(f"← Raw response (header={header}): {payload_str}")

    def closeEvent(self, event):
        if self.sock:
            self.sock.close()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = LoginWindow()
    win.show()
    sys.exit(app.exec_())
