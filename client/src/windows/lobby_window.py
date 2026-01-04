from PyQt5 import QtWidgets, QtCore
import sys
from pathlib import Path

# Thêm utils vào đường dẫn
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.image_utils import set_window_icon
from components.user_header import UserHeader
from utils.connection_monitor import ConnectionMonitor


class LobbyWindow(QtWidgets.QWidget):
    """Cửa sổ Lobby - danh sách phòng và tạo phòng"""
    
    # Các biến hằng từ server
    MAX_PLAYERS_PER_ROOM = 12
    MIN_PLAYERS_TO_START = 6
    ROOM_WAITING = 0
    ROOM_PLAYING = 1
    
    def __init__(self, toast_manager, window_manager):
        super().__init__()
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.network_client = None

        self.setObjectName("lobby_window")
        self.setup_ui()

        # Timers
        self.recv_timer = QtCore.QTimer()
        self.recv_timer.timeout.connect(self.receive_packets)

        self.auto_refresh_timer = QtCore.QTimer()
        self.auto_refresh_timer.timeout.connect(self.on_refresh_rooms)

        # Connection monitor
        self.connection_monitor = None
        
    def setup_ui(self):
        """Set up giao diện người dùng"""
        self.setWindowTitle("Werewolf - Lobby")
        self.resize(900, 700)
        set_window_icon(self)
        
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # Header người dùng (username + logout)
        self.user_header = UserHeader(self)
        self.user_header.logout_clicked.connect(self.on_logout)
        main_layout.addWidget(self.user_header)
        
        # Header với biểu tượng
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addStretch()
        
        # Village icon
        village_icon = QtWidgets.QLabel("🏘️")
        village_icon.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(village_icon)
        
        # Welcome label
        self.welcome_label = QtWidgets.QLabel("Welcome, Player!")
        self.welcome_label.setObjectName("welcome_label")
        self.welcome_label.setAlignment(QtCore.Qt.AlignCenter)
        header_layout.addWidget(self.welcome_label)
        
        # Moon icon
        moon_icon = QtWidgets.QLabel("🌙")
        moon_icon.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(moon_icon)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Nhóm component tạo phòng mới
        create_group = QtWidgets.QGroupBox("Create New Room")
        create_group.setObjectName("create_room_group")
        create_layout = QtWidgets.QHBoxLayout()
        
        create_layout.addWidget(QtWidgets.QLabel("Room Name:"))
        self.room_name_input = QtWidgets.QLineEdit()
        self.room_name_input.setObjectName("room_name_input")
        self.room_name_input.setPlaceholderText("Enter room name...")
        create_layout.addWidget(self.room_name_input)
        
        self.create_room_button = QtWidgets.QPushButton("Create Room")
        self.create_room_button.setObjectName("create_room_button")
        create_layout.addWidget(self.create_room_button)
        
        create_group.setLayout(create_layout)
        main_layout.addWidget(create_group)
        
        # Nhóm danh sách phòng
        room_group = QtWidgets.QGroupBox("Available Rooms")
        room_group.setObjectName("room_list_group")
        room_layout = QtWidgets.QVBoxLayout()
        
        # Khu vực cuộn cho danh sách phòng
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        # Container widget cho các thẻ phòng
        self.room_container = QtWidgets.QWidget()
        self.room_grid_layout = QtWidgets.QGridLayout(self.room_container)
        self.room_grid_layout.setSpacing(15)
        self.room_grid_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll_area.setWidget(self.room_container)
        room_layout.addWidget(scroll_area)
        
        self.refresh_button = QtWidgets.QPushButton("🔄 Refresh Room List")
        self.refresh_button.setObjectName("refresh_button")
        self.refresh_button.setMinimumHeight(35)
        room_layout.addWidget(self.refresh_button)
        
        room_group.setLayout(room_layout)
        main_layout.addWidget(room_group)
        
        # Kết nối 
        self.create_room_button.clicked.connect(self.on_create_room)
        self.refresh_button.clicked.connect(self.on_refresh_rooms)
        
    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)

        # Lấy client và tên người dùng từ window manager
        self.network_client = self.window_manager.get_shared_data("network_client")
        username = self.window_manager.get_shared_data("username")

        if username:
            self.welcome_label.setText(f"Welcome, {username}! 🎮")
            self.user_header.set_username(username)

        # Bắt đầu nhận gói tin
        self.recv_timer.start(100)

        # Lấy danh sách phòng ban đầu
        self.on_refresh_rooms()

        # Bắt đầu tự động làm mới (mỗi 3 giây)
        self.auto_refresh_timer.start(3000)

        # Setup connection monitor
        if not self.connection_monitor:
            self.connection_monitor = ConnectionMonitor(
                self.network_client,
                self.toast_manager,
                self.window_manager
            )
            self.connection_monitor.connection_lost.connect(self.on_connection_lost)
            self.connection_monitor.connection_restored.connect(self.on_connection_restored)
        self.connection_monitor.start()
        
    def hideEvent(self, event):
        """Called when window is hidden"""
        super().hideEvent(event)
        self.recv_timer.stop()
        self.auto_refresh_timer.stop()
        if self.connection_monitor:
            self.connection_monitor.stop()
        
    def on_create_room(self):
        """Tạo phòng mới"""
        room_name = self.room_name_input.text().strip()
        
        if not room_name:
            self.toast_manager.warning("Please enter a room name")
            return
            
        try:
            payload = {"room_name": room_name}
            self.network_client.send_packet(203, payload)  # CREATE_ROOM_REQ
            self.room_name_input.clear()
        except Exception as e:
            self.toast_manager.error(f"Failed to create room: {str(e)}")
            
    def on_refresh_rooms(self):
        """Làm mới danh sách phòng"""
        try:
            self.network_client.send_packet(201, {})  # GET_ROOMS_REQ
        except Exception as e:
            self.toast_manager.error(f"Failed to refresh: {str(e)}")
            
    def join_room(self, room_id):
        """Tham gia phòng"""
        try:
            payload = {"room_id": room_id}
            self.network_client.send_packet(205, payload)  # JOIN_ROOM_REQ
        except Exception as e:
            self.toast_manager.error(f"Failed to join room: {str(e)}")
            
    def receive_packets(self):
        """Nhận gói tin từ server"""
        try:
            header, payload = self.network_client.receive_packet()

            if header is None:
                return

            self.handle_packet(header, payload)
            
        except RuntimeError as e:
            error_msg = str(e)
            # Kiểm tra xem có phải server disconnect không
            if "Server closed" in error_msg or "Receive failed" in error_msg:
                print(f"[ERROR] Server disconnected: {error_msg}")
                self.handle_server_disconnect()
            else:
                self.toast_manager.error(f"Receive error: {error_msg}")
        except ConnectionError as e:
            # Connection lost detected
            print(f"[DEBUG] Connection lost: {e}")
            self.recv_timer.stop()
            self.auto_refresh_timer.stop()

            # Trigger connection lost handling via monitor
            if self.connection_monitor:
                self.connection_monitor.is_connected = False
                self.connection_monitor.stop()
                self.connection_monitor.handle_connection_lost()
        except Exception as e:
            # Other errors - just show toast
            error_msg = str(e)
            print(f"[DEBUG] Other error: {error_msg}")
            self.toast_manager.error(f"Receive error: {error_msg}")
            
    def handle_server_disconnect(self):
        """Xử lý khi server disconnect"""
        print("[DEBUG] Handling server disconnect...")
        # Dừng timers
        self.recv_timer.stop()
        self.auto_refresh_timer.stop()
        
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
        self.window_manager.set_shared_data("user_id", None)
        self.window_manager.set_shared_data("username", None)
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
        elif header == 202:  # GET_ROOMS_RES
            self.update_room_table(payload)
            
        elif header == 204:  # CREATE_ROOM_RES
            if payload.get("status") == "success":
                room_id = payload.get("room_id")
                room_name = payload.get("room_name")
                
                self.toast_manager.success(f"Room '{room_name}' created!")
                
                # Lưu dữ liệu phòng và chuyển hướng
                self.window_manager.set_shared_data("current_room_id", room_id)
                self.window_manager.set_shared_data("current_room_name", room_name)
                self.window_manager.set_shared_data("is_host", True)
                # Creator is first player, so initial count is 1
                username = self.window_manager.get_shared_data("username")
                self.window_manager.set_shared_data("room_players", [{"username": username}])
                
                self.window_manager.navigate_to("room")
            else:
                msg = payload.get("message", "Unknown error")
                self.toast_manager.error(f"Failed to create room: {msg}")
                
        elif header == 206:  # JOIN_ROOM_RES
            if payload.get("status") == "success":
                room_id = payload.get("room_id")
                room_name = payload.get("room_name")
                is_host = payload.get("is_host", 0) == 1
                
                self.toast_manager.success(f"Joined room '{room_name}'!")
                
                # Lưu dữ liệu phòng và chuyển hướng
                self.window_manager.set_shared_data("current_room_id", room_id)
                self.window_manager.set_shared_data("current_room_name", room_name)
                self.window_manager.set_shared_data("is_host", is_host)
                self.window_manager.set_shared_data("room_players", payload.get("players", []))
                
                self.window_manager.navigate_to("room")
            else:
                msg = payload.get("message", "Unknown error")
                self.toast_manager.error(f"Failed to join room: {msg}")
                
    def update_room_table(self, rooms):
        """Cập nhật grid cards với danh sách phòng"""
        # Xóa các thẻ hiện có
        for i in reversed(range(self.room_grid_layout.count())):
            widget = self.room_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        
        # Tạo các thẻ phòng (3-4 mỗi hàng)
        columns = 3  # 3 rooms per row
        for i, room in enumerate(rooms):
            room_id = room.get("id", 0)
            name = room.get("name", "Unknown")
            current = room.get("current", 0)
            max_players = room.get("max", self.MAX_PLAYERS_PER_ROOM)
            status = room.get("status", 0)
            
            # Tạo thẻ phòng
            card = self.create_room_card(room_id, name, current, max_players, status)
            
            # Thêm vào lưới (hàng, cột)
            row = i // columns
            col = i % columns
            self.room_grid_layout.addWidget(card, row, col)
        
        # Thêm spacer để đẩy các thẻ lên trên
        self.room_grid_layout.setRowStretch(len(rooms) // columns + 1, 1)
    
    def create_room_card(self, room_id, name, current, max_players, status):
        """Tạo card cho một phòng chơi"""
        card = QtWidgets.QFrame()
        card.setObjectName("room_card")
        card.setFrameShape(QtWidgets.QFrame.StyledPanel)
        card.setStyleSheet("""
            QFrame#room_card {
                background-color: #16213e;
                border: 2px solid #0f3460;
                border-radius: 10px;
                padding: 10px;
            }
            QFrame#room_card:hover {
                border-color: #e94560;
            }
        """)
        
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(8)
        
        # Header với biểu tượng và tên phòng
        header_layout = QtWidgets.QHBoxLayout()
        
        icon_label = QtWidgets.QLabel("🏠")
        icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_label)
        
        room_name_label = QtWidgets.QLabel(name)
        room_name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #eaeaea;")
        room_name_label.setWordWrap(True)
        header_layout.addWidget(room_name_label, 1)
        
        card_layout.addLayout(header_layout)
        
        # Room ID
        id_label = QtWidgets.QLabel(f"Room #{room_id}")
        id_label.setStyleSheet("font-size: 11px; color: #888888;")
        card_layout.addWidget(id_label)
        
        # Players count
        players_label = QtWidgets.QLabel(f"👥 {current}/{max_players} players")
        players_label.setStyleSheet("font-size: 13px; color: #aaaaaa;")
        card_layout.addWidget(players_label)
        
        # Status
        status_text = "WAITING" if status == self.ROOM_WAITING else "PLAYING"
        status_color = "#2ecc71" if status == self.ROOM_WAITING else "#e74c3c"
        status_label = QtWidgets.QLabel(f"● {status_text}")
        status_label.setStyleSheet(f"font-size: 12px; color: {status_color}; font-weight: bold;")
        card_layout.addWidget(status_label)
        
        # Join button
        if status == self.ROOM_WAITING and current < max_players:
            join_button = QtWidgets.QPushButton("Join Room")
            join_button.setObjectName("join_room_button")
            join_button.setMinimumHeight(35)
            join_button.setStyleSheet("""
                QPushButton#join_room_button {
                    background-color: #e94560;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton#join_room_button:hover {
                    background-color: #ff5770;
                }
                QPushButton#join_room_button:pressed {
                    background-color: #d03550;
                }
            """)
            join_button.clicked.connect(lambda checked, rid=room_id: self.join_room(rid))
            card_layout.addWidget(join_button)
        else:
            full_label = QtWidgets.QLabel("FULL" if current >= max_players else "IN GAME")
            full_label.setAlignment(QtCore.Qt.AlignCenter)
            full_label.setStyleSheet("""
                background-color: #555555;
                color: #888888;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            """)
            card_layout.addWidget(full_label)
        
        return card
    
    def on_connection_lost(self):
        """Handle connection lost"""
        self.recv_timer.stop()
        self.auto_refresh_timer.stop()

    def on_connection_restored(self):
        """Handle connection restored after reconnect"""
        print("[DEBUG] Lobby: Connection restored, navigating to login")
        # Stop timers
        self.recv_timer.stop()
        self.auto_refresh_timer.stop()

        # Clear session data
        self.window_manager.set_shared_data("user_id", None)
        self.window_manager.set_shared_data("username", None)

        # Navigate to login screen
        self.window_manager.navigate_to("login")

    def on_logout(self):
        """Handle logout button click"""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            try:
                # Send logout request
                self.network_client.send_packet(105, {})  # LOGOUT_REQ
                self.toast_manager.info("Logging out...")

                # Stop timers
                self.recv_timer.stop()
                self.auto_refresh_timer.stop()

                # Clear shared data
                self.window_manager.set_shared_data("user_id", None)
                self.window_manager.set_shared_data("username", None)
                self.window_manager.set_shared_data("connected", False)

                # KHÔNG disconnect network_client - chỉ clear session
                # Network client vẫn giữ kết nối để có thể login lại

                # Navigate to welcome
                self.window_manager.navigate_to("welcome")

            except Exception as e:
                self.toast_manager.error(f"Logout error: {str(e)}")
    
    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ - cleanup network client"""
        self.recv_timer.stop()
        self.auto_refresh_timer.stop()
        if self.connection_monitor:
            self.connection_monitor.stop()
        
        # Cleanup network client giống như Ctrl+C
        print("[DEBUG] Lobby window closing, cleaning up...")
        try:
            if self.network_client:
                self.network_client.disconnect()
                self.network_client.destroy()
        except Exception as e:
            print(f"[ERROR] Error during lobby cleanup: {e}")
        
        event.accept()
        # Quit application
        QtWidgets.QApplication.instance().quit()
