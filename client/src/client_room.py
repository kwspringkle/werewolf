import sys
import socket
import json
from PyQt5 import QtWidgets, QtCore

class RoomClient(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.sock = None
        self.user_id = None
        self.username = None
        self.current_room_id = None
        self.is_host = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Werewolf Game - Room Management")
        self.resize(900, 700)

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

        # Room List section
        room_list_group = QtWidgets.QGroupBox("Available Rooms")
        room_list_layout = QtWidgets.QVBoxLayout()

        self.room_table = QtWidgets.QTableWidget()
        self.room_table.setColumnCount(5)
        self.room_table.setHorizontalHeaderLabels(["ID", "Name", "Players", "Status", "Action"])
        self.room_table.horizontalHeader().setStretchLastSection(True)
        self.room_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.btn_refresh_rooms = QtWidgets.QPushButton("Refresh Room List")
        self.btn_refresh_rooms.setEnabled(False)

        room_list_layout.addWidget(self.room_table)
        room_list_layout.addWidget(self.btn_refresh_rooms)
        room_list_group.setLayout(room_list_layout)

        # Create Room section
        create_room_group = QtWidgets.QGroupBox("Create New Room")
        create_room_layout = QtWidgets.QHBoxLayout()
        self.room_name_input = QtWidgets.QLineEdit()
        self.room_name_input.setPlaceholderText("Enter room name...")
        self.btn_create_room = QtWidgets.QPushButton("Create Room")
        self.btn_create_room.setEnabled(False)
        create_room_layout.addWidget(QtWidgets.QLabel("Room Name:"))
        create_room_layout.addWidget(self.room_name_input)
        create_room_layout.addWidget(self.btn_create_room)
        create_room_group.setLayout(create_room_layout)

        # Current Room section
        current_room_group = QtWidgets.QGroupBox("Current Room")
        current_room_layout = QtWidgets.QVBoxLayout()

        self.room_info_label = QtWidgets.QLabel("Not in any room")
        self.room_info_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.player_list = QtWidgets.QListWidget()
        self.player_list.setMaximumHeight(150)

        room_actions_layout = QtWidgets.QHBoxLayout()
        self.btn_start_game = QtWidgets.QPushButton("Start Game")
        self.btn_start_game.setEnabled(False)
        self.btn_start_game.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        self.btn_leave_room = QtWidgets.QPushButton("Leave Room")
        self.btn_leave_room.setEnabled(False)
        room_actions_layout.addWidget(self.btn_start_game)
        room_actions_layout.addWidget(self.btn_leave_room)

        current_room_layout.addWidget(self.room_info_label)
        current_room_layout.addWidget(QtWidgets.QLabel("Players:"))
        current_room_layout.addWidget(self.player_list)
        current_room_layout.addLayout(room_actions_layout)
        current_room_group.setLayout(current_room_layout)

        # Main layout
        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(conn_group)
        left_layout.addWidget(login_group)
        left_layout.addWidget(create_room_group)
        left_layout.addWidget(current_room_group)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(room_list_group)

        content_layout = QtWidgets.QHBoxLayout()
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setMaximumWidth(400)
        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right_layout)
        content_layout.addWidget(left_widget)
        content_layout.addWidget(right_widget)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(content_layout)
        main_layout.addWidget(QtWidgets.QLabel("Log:"))
        main_layout.addWidget(self.log)
        self.setLayout(main_layout)

        # Connect signals
        self.btn_connect.clicked.connect(self.connect_server)
        self.btn_login.clicked.connect(self.do_login)
        self.btn_refresh_rooms.clicked.connect(self.get_rooms)
        self.btn_create_room.clicked.connect(self.create_room)
        self.btn_leave_room.clicked.connect(self.leave_room)
        self.btn_start_game.clicked.connect(self.start_game)

        # Receive timer
        self.recv_timer = QtCore.QTimer()
        self.recv_timer.timeout.connect(self.receive_packet)

        # Auto refresh room list timer (every 3 seconds)
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh_rooms)

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

        payload = {"username": username, "password": password}
        self.send_packet(101, payload)  # LOGIN_REQ

    def get_rooms(self):
        self.send_packet(201, {})  # GET_ROOMS_REQ

    def auto_refresh_rooms(self):
        # Only auto-refresh when logged in and not in a room
        if self.user_id and not self.current_room_id:
            self.get_rooms()

    def create_room(self):
        room_name = self.room_name_input.text().strip()
        if not room_name:
            self.log.append("✗ Please enter room name")
            return

        payload = {"room_name": room_name}
        self.send_packet(203, payload)  # CREATE_ROOM_REQ

    def join_room(self, room_id):
        payload = {"room_id": room_id}
        self.send_packet(205, payload)  # JOIN_ROOM_REQ

    def leave_room(self):
        self.send_packet(208, {})  # LEAVE_ROOM_REQ

    def start_game(self):
        if not self.current_room_id:
            self.log.append("✗ You are not in a room")
            return

        payload = {"room_id": self.current_room_id}
        self.send_packet(301, payload)  # START_GAME_REQ

    def receive_packet(self):
        try:
            header_bytes = self.sock.recv(2)
            if not header_bytes or len(header_bytes) < 2:
                return

            header = int.from_bytes(header_bytes, "big")

            length_bytes = self.sock.recv(4)
            if len(length_bytes) < 4:
                return

            length = int.from_bytes(length_bytes, "big")

            payload_bytes = b""
            while len(payload_bytes) < length:
                chunk = self.sock.recv(length - len(payload_bytes))
                if not chunk:
                    break
                payload_bytes += chunk

            payload_str = payload_bytes.decode('utf-8')
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
                    self.user_id = data.get("user_id")
                    self.username = data.get("username")
                    self.log.append(f"   ✓ Login successful! Welcome {self.username} (ID: {self.user_id})")
                    self.btn_login.setEnabled(False)
                    self.btn_refresh_rooms.setEnabled(True)
                    self.btn_create_room.setEnabled(True)

                    # Get rooms immediately and start auto-refresh
                    self.get_rooms()
                    self.refresh_timer.start(3000)  # Refresh every 3 seconds
                    self.log.append("   → Auto-refresh enabled (every 3s)")
                else:
                    msg = data.get("message", "Unknown error")
                    self.log.append(f"   ✗ Login failed: {msg}")

            elif header == 202:  # GET_ROOMS_RES
                self.log.append(f"← ROOM LIST RECEIVED ({len(data)} rooms)")
                self.update_room_table(data)

            elif header == 204:  # CREATE_ROOM_RES
                self.log.append(f"← CREATE ROOM RESPONSE:")
                if data.get("status") == "success":
                    self.current_room_id = data.get("room_id")
                    room_name = data.get("room_name")
                    self.is_host = True
                    self.log.append(f"   ✓ Room created: {room_name} (ID: {self.current_room_id})")
                    self.room_info_label.setText(f"Room: {room_name} (ID: {self.current_room_id}) - You are HOST")
                    self.btn_leave_room.setEnabled(True)
                    self.btn_start_game.setEnabled(True)
                    self.btn_create_room.setEnabled(False)
                    self.room_name_input.clear()
                    self.player_list.clear()
                    self.player_list.addItem(f"👑 {self.username} (You, Host)")

                    # Stop auto-refresh when in a room
                    self.refresh_timer.stop()
                else:
                    msg = data.get("message", "Unknown error")
                    self.log.append(f"   ✗ Failed to create room: {msg}")

            elif header == 206:  # JOIN_ROOM_RES
                self.log.append(f"← JOIN ROOM RESPONSE:")
                if data.get("status") == "success":
                    self.current_room_id = data.get("room_id")
                    room_name = data.get("room_name")
                    self.is_host = data.get("is_host", 0) == 1
                    players = data.get("players", [])

                    host_text = " - You are HOST" if self.is_host else ""
                    self.log.append(f"   ✓ Joined room: {room_name} (ID: {self.current_room_id})")
                    self.room_info_label.setText(f"Room: {room_name} (ID: {self.current_room_id}){host_text}")
                    self.btn_leave_room.setEnabled(True)
                    self.btn_create_room.setEnabled(False)

                    if self.is_host:
                        self.btn_start_game.setEnabled(True)

                    self.player_list.clear()
                    for p in players:
                        username = p.get("username", "Unknown")
                        if username == self.username:
                            self.player_list.addItem(f"👤 {username} (You)")
                        else:
                            self.player_list.addItem(f"👤 {username}")

                    # Stop auto-refresh when in a room
                    self.refresh_timer.stop()
                else:
                    msg = data.get("message", "Unknown error")
                    self.log.append(f"   ✗ Failed to join room: {msg}")

            elif header == 207:  # ROOM_STATUS_UPDATE
                update_type = data.get("type")
                if update_type == "player_joined":
                    username = data.get("username")
                    current = data.get("current_players")
                    self.log.append(f"   → {username} joined the room ({current} players)")
                    if username != self.username:
                        self.player_list.addItem(f"👤 {username}")
                
                elif update_type == "player_left":
                    username = data.get("username")
                    current = data.get("current_players")
                    new_host = data.get("new_host")  # ✅ Lấy thông tin host mới
                    
                    self.log.append(f"   ← {username} left the room ({current} players)")
                    
                    # Xóa player khỏi list
                    for i in range(self.player_list.count()):
                        if username in self.player_list.item(i).text():
                            self.player_list.takeItem(i)
                            break
                    
                    # ✅ Xử lý host mới
                    if new_host:
                        self.log.append(f"   👑 {new_host} is now the host")
                        
                        # Nếu bạn là host mới
                        if new_host == self.username:
                            self.is_host = True
                            self.btn_start_game.setEnabled(True)
                            self.room_info_label.setText(
                                f"{self.room_info_label.text().split(' -')[0]} - You are HOST"
                            )
                            self.log.append("   ✓ You are now the host!")
                        
                        # Cập nhật player list để hiển thị icon 👑 cho host mới
                        self.update_player_list_icons(new_host)
                
                elif update_type == "player_disconnected":
                    username = data.get("username")
                    game_started = data.get("game_started", False)
                    new_host = data.get("new_host")
                    
                    if game_started:
                        self.log.append(f"   ☠️ {username} disconnected (marked as dead)")
                    else:
                        self.log.append(f"   ⚠️ {username} disconnected")
                        for i in range(self.player_list.count()):
                            if username in self.player_list.item(i).text():
                                self.player_list.takeItem(i)
                                break
                        
                        # Xử lý host mới khi disconnect
                        if new_host:
                            self.log.append(f"   👑 {new_host} is now the host")
                            if new_host == self.username:
                                self.is_host = True
                                self.btn_start_game.setEnabled(True)
                                self.room_info_label.setText(
                                    f"{self.room_info_label.text().split(' -')[0]} - You are HOST"
                                )
                                self.log.append("   ✓ You are now the host!")
                            self.update_player_list_icons(new_host)

            elif header == 209:  # LEAVE_ROOM_RES
                self.log.append(f"← LEAVE ROOM RESPONSE:")
                if data.get("status") == "success":
                    self.log.append(f"   ✓ Left room successfully")
                    self.current_room_id = None
                    self.is_host = False
                    self.room_info_label.setText("Not in any room")
                    self.player_list.clear()
                    self.btn_leave_room.setEnabled(False)
                    self.btn_start_game.setEnabled(False)
                    self.btn_create_room.setEnabled(True)

                    # Resume auto-refresh when leaving room
                    self.get_rooms()
                    self.refresh_timer.start(3000)
                    self.log.append("   → Auto-refresh resumed")
                else:
                    msg = data.get("message", "Unknown error")
                    self.log.append(f"   ✗ Failed to leave room: {msg}")

            elif header == 302:  # GAME_START_RES_AND_ROLE
                self.log.append(f"← GAME STARTED!")
                if data.get("status") == "success":
                    role = data.get("role", 0)
                    role_name = data.get("role_name", "Unknown")
                    description = data.get("role_description", "")

                    self.log.append(f"   ✓ Your role: {role_name}")
                    self.log.append(f"   📜 {description}")

                    # ✅ Đổi từ "teammates" thành "werewolf_team"
                    teammates = data.get("werewolf_team", [])
                    if teammates and len(teammates) > 0:
                        self.log.append(f"   🐺 Your werewolf teammates:")
                        for mate in teammates:
                            # Nếu server gửi string thay vì object
                            if isinstance(mate, str):
                                self.log.append(f"      • {mate}")
                            else:
                                # Nếu server gửi object với username và user_id
                                username = mate.get("username", "Unknown") if isinstance(mate, dict) else mate
                                self.log.append(f"      • {username}")

                    # Disable buttons
                    self.btn_start_game.setEnabled(False)
                    self.btn_leave_room.setText("Surrender")
                    self.btn_create_room.setEnabled(False)
                    self.btn_refresh_rooms.setEnabled(False)

            else:
                self.log.append(f"← Received header={header}: {payload_str}")

        except json.JSONDecodeError:
            self.log.append(f"← Raw response (header={header}): {payload_str}")

    def update_player_list_icons(self, new_host_username):
        """Cập nhật icon 👑 cho host mới trong player list"""
        for i in range(self.player_list.count()):
            item = self.player_list.item(i)
            text = item.text()
            
            # Xóa icon 👑 cũ
            if text.startswith("👑"):
                text = text.replace("👑", "👤", 1)
            
            # Lấy username từ text (bỏ các suffix như "(You)", "(Host)")
            username = text.split("(")[0].replace("👤", "").strip()
            
            # Thêm icon 👑 cho host mới
            if username == new_host_username:
                if "(You)" in text:
                    text = f"👑 {username} (You, Host)"
                else:
                    text = f"👑 {username} (Host)"
            elif "(You)" in text:
                text = f"👤 {username} (You)"
            else:
                text = f"👤 {username}"
            
            item.setText(text)

    def update_room_table(self, rooms):
        self.room_table.setRowCount(len(rooms))

        for i, room in enumerate(rooms):
            room_id = room.get("id", 0)
            name = room.get("name", "Unknown")
            current = room.get("current", 0)
            max_players = room.get("max", 12)
            status = room.get("status", 0)

            status_text = "WAITING" if status == 0 else "PLAYING"
            status_color = "green" if status == 0 else "red"

            self.room_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(room_id)))
            self.room_table.setItem(i, 1, QtWidgets.QTableWidgetItem(name))
            self.room_table.setItem(i, 2, QtWidgets.QTableWidgetItem(f"{current}/{max_players}"))

            status_item = QtWidgets.QTableWidgetItem(status_text)
            status_item.setForeground(QtCore.Qt.white)
            status_item.setBackground(QtCore.Qt.green if status == 0 else QtCore.Qt.red)
            self.room_table.setItem(i, 3, status_item)

            if status == 0 and current < max_players and not self.current_room_id:
                btn_join = QtWidgets.QPushButton("Join")
                btn_join.clicked.connect(lambda checked, rid=room_id: self.join_room(rid))
                self.room_table.setCellWidget(i, 4, btn_join)
            else:
                self.room_table.setItem(i, 4, QtWidgets.QTableWidgetItem(""))

    def closeEvent(self, event):
        self.recv_timer.stop()
        self.refresh_timer.stop()
        if self.sock:
            self.sock.close()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = RoomClient()
    win.show()
    sys.exit(app.exec_())
