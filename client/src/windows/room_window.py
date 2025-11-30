from PyQt5 import QtWidgets, QtCore
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.image_utils import set_window_icon
from components.user_header import UserHeader
from windows.role_card_window import RoleCardWindow


class RoomWindow(QtWidgets.QWidget):    
    # Biến hằng từ server
    MIN_PLAYERS = 6  
    MAX_PLAYERS_PER_ROOM = 12
    
    def __init__(self, toast_manager, window_manager):
        super().__init__()
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.network_client = None
        self.current_room_id = None
        self.is_host = False
        self.current_player_count = 0
        
        self.setObjectName("room_window")
        self.setup_ui()
        
        # Timer
        self.recv_timer = QtCore.QTimer()
        self.recv_timer.timeout.connect(self.receive_packets)
        
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        self.setWindowTitle("Werewolf - Room")
        self.resize(700, 600)

        set_window_icon(self)
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # User header (username + logout)
        self.user_header = UserHeader(self)
        self.user_header.logout_clicked.connect(self.on_logout)
        main_layout.addWidget(self.user_header)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addStretch()
        
        wolf_icon = QtWidgets.QLabel("🐺")
        wolf_icon.setStyleSheet("font-size: 40px;")
        header_layout.addWidget(wolf_icon)
        
        # Room title
        self.room_title_label = QtWidgets.QLabel("Room Name")
        self.room_title_label.setObjectName("room_title_label")
        self.room_title_label.setAlignment(QtCore.Qt.AlignCenter)
        header_layout.addWidget(self.room_title_label)
        
        wolf_icon2 = QtWidgets.QLabel("🐺")
        wolf_icon2.setStyleSheet("font-size: 40px;")
        header_layout.addWidget(wolf_icon2)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Room info
        self.room_info_label = QtWidgets.QLabel("Room ID: 0 | Status: Waiting")
        self.room_info_label.setObjectName("room_info_label")
        self.room_info_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.room_info_label)
        
        # Players group
        players_group = QtWidgets.QGroupBox("Players in Room")
        players_group.setObjectName("players_group")
        players_layout = QtWidgets.QVBoxLayout()
        
        # Thông tin số lượng người chơi
        self.player_count_label = QtWidgets.QLabel(f"Players: 0/{self.MAX_PLAYERS_PER_ROOM}")
        self.player_count_label.setObjectName("player_count_label")
        self.player_count_label.setAlignment(QtCore.Qt.AlignCenter)
        players_layout.addWidget(self.player_count_label)
        
        # Cảnh báo số lượng người chơi tối thiểu
        self.min_players_label = QtWidgets.QLabel(f"⚠️ Minimum {self.MIN_PLAYERS} players required to start")
        self.min_players_label.setObjectName("min_players_label")
        self.min_players_label.setAlignment(QtCore.Qt.AlignCenter)
        self.min_players_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        self.min_players_label.setVisible(True)
        players_layout.addWidget(self.min_players_label)
        
        self.player_list = QtWidgets.QListWidget()
        self.player_list.setObjectName("player_list")
        players_layout.addWidget(self.player_list)
        
        players_group.setLayout(players_layout)
        main_layout.addWidget(players_group)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.start_game_button = QtWidgets.QPushButton("Start Game")
        self.start_game_button.setObjectName("start_game_button")
        self.start_game_button.setMinimumHeight(40)
        self.start_game_button.setEnabled(False)
        self.start_game_button.setVisible(False)  # Hidden by default, shown only for host
        button_layout.addWidget(self.start_game_button)
        
        self.leave_room_button = QtWidgets.QPushButton("Leave Room")
        self.leave_room_button.setObjectName("leave_room_button")
        self.leave_room_button.setMinimumHeight(40)
        button_layout.addWidget(self.leave_room_button)
        
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.start_game_button.clicked.connect(self.on_start_game)
        self.leave_room_button.clicked.connect(self.on_leave_room)
        
    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)
        
        # Get shared data
        self.network_client = self.window_manager.get_shared_data("network_client")
        self.current_room_id = self.window_manager.get_shared_data("current_room_id")
        room_name = self.window_manager.get_shared_data("current_room_name")
        self.is_host = self.window_manager.get_shared_data("is_host", False)
        username = self.window_manager.get_shared_data("username")
        
        # Update UI
        self.room_title_label.setText(f"🏠 {room_name}")
        
        host_text = " - You are HOST 👑" if self.is_host else ""
        self.room_info_label.setText(f"Room ID: {self.current_room_id}{host_text}")
        
        # Set username in header
        if username:
            self.user_header.set_username(username)
        
        # Show and enable start button only for host
        self.start_game_button.setVisible(self.is_host)
        if self.is_host:
            self.start_game_button.setEnabled(False)  # Will be enabled when enough players
        
        # Load players
        players = self.window_manager.get_shared_data("room_players", [])
        self.update_player_list(players, username)
        self.current_player_count = len(players)
        self.update_player_count_ui()
        
        # Start receiving
        self.recv_timer.start(100)
        
    def hideEvent(self, event):
        """Called when window is hidden"""
        super().hideEvent(event)
        self.recv_timer.stop()
        
    def update_player_list(self, players, current_username):
        """Cập nhật widget danh sách người chơi"""
        self.player_list.clear()
        
        for player in players:
            username = player.get("username", "Unknown")
            
            if username == current_username:
                self.player_list.addItem(f"👤 {username} (You)")
            else:
                self.player_list.addItem(f"👤 {username}")
                
    def update_player_count_ui(self):
        """Cập nhật nhãn số lượng người chơi và trạng thái nút bắt đầu"""
        # Update label
        if self.current_player_count < self.MIN_PLAYERS:
            status_text = f"⚠️ Players: {self.current_player_count}/{self.MAX_PLAYERS_PER_ROOM} (Need {self.MIN_PLAYERS} to start)"
            self.player_count_label.setStyleSheet("font-size: 14px; color: #e74c3c; padding: 5px; font-weight: bold;")
        else:
            status_text = f"✓ Players: {self.current_player_count}/{self.MAX_PLAYERS_PER_ROOM} (Ready to start!)"
            self.player_count_label.setStyleSheet("font-size: 14px; color: #2ecc71; padding: 5px; font-weight: bold;")
        
        self.player_count_label.setText(status_text)
        
        # Cập nhật trạng thái nút bắt đầu
        if self.is_host:
            can_start = self.current_player_count >= self.MIN_PLAYERS
            self.start_game_button.setEnabled(can_start)
            
            if not can_start:
                self.start_game_button.setToolTip(f"Need at least {self.MIN_PLAYERS} players to start")
                # Gray out when disabled
                self.start_game_button.setStyleSheet("""
                    QPushButton:disabled {
                        background-color: #555555;
                        color: #888888;
                        border: 1px solid #444444;
                    }
                """)
            else:
                self.start_game_button.setToolTip("Start the game!")
                # Reset style when enabled
                self.start_game_button.setStyleSheet("")
                
    def on_start_game(self):
        """Xử lý khi nhấn nút bắt đầu"""
        if not self.is_host:
            self.toast_manager.warning("Only host can start the game")
            return
        
        # Check minimum players
        if self.current_player_count < self.MIN_PLAYERS:
            self.toast_manager.warning(
                f"Cannot start game! Need at least {self.MIN_PLAYERS} players. "
                f"Currently: {self.current_player_count}"
            )
            return
            
        try:
            payload = {"room_id": self.current_room_id}
            self.network_client.send_packet(301, payload)  # START_GAME_REQ
            self.toast_manager.info(f"Starting game with {self.current_player_count} players...")
        except Exception as e:
            self.toast_manager.error(f"Failed to start game: {str(e)}")
            
    def on_leave_room(self):
        """Xử lý khi nhấn nút rời phòng"""
        try:
            self.network_client.send_packet(208, {})  # LEAVE_ROOM_REQ
        except Exception as e:
            self.toast_manager.error(f"Failed to leave room: {str(e)}")
            
    def receive_packets(self):
        """Nhận gói tin từ server"""
        try:
            header, payload = self.network_client.receive_packet()
            
            if header is None:
                return
                
            self.handle_packet(header, payload)
            
        except Exception as e:
            self.toast_manager.error(f"Receive error: {str(e)}")
            
    def handle_packet(self, header, payload):
        """Xử lý gói tin nhận được"""
        username = self.window_manager.get_shared_data("username")
        
        if header == 207:  # ROOM_STATUS_UPDATE
            update_type = payload.get("type")
            
            if update_type == "player_joined":
                player_username = payload.get("username")
                current = payload.get("current_players", 0)
                self.current_player_count = current
                
                # Show notification for all players
                self.toast_manager.info(f"👤 {player_username} joined the room ({current} players)")
                
                # Add to list if not already there (for host receiving the update)
                if player_username != username:
                    # Check if player already in list
                    player_exists = False
                    for i in range(self.player_list.count()):
                        if player_username in self.player_list.item(i).text():
                            player_exists = True
                            break
                    
                    if not player_exists:
                        self.player_list.addItem(f"👤 {player_username}")
                
                # Update UI
                self.update_player_count_ui()
                    
            elif update_type == "player_left":
                player_username = payload.get("username")
                current = payload.get("current_players", 0)
                self.current_player_count = current
                
                self.toast_manager.warning(f"{player_username} left ({current} players)")
                
                # Remove from list
                for i in range(self.player_list.count()):
                    if player_username in self.player_list.item(i).text():
                        self.player_list.takeItem(i)
                        break
                
                # Update UI
                self.update_player_count_ui()
                
                # Extra warning for host if below minimum
                if self.is_host and current < self.MIN_PLAYERS:
                    needed = self.MIN_PLAYERS - current
                    self.toast_manager.warning(f"⚠️ Need {needed} more player{'s' if needed > 1 else ''} to start!")
                    
            elif update_type == "player_disconnected":
                player_username = payload.get("username")
                message = payload.get("message", "Player disconnected")
                
                self.toast_manager.error(f"💀 {player_username} disconnected - Marked as DEAD")
                
                # Mark player as dead in list (strikethrough)
                for i in range(self.player_list.count()):
                    item = self.player_list.item(i)
                    if player_username in item.text() and "💀" not in item.text():
                        # Update item text with skull icon
                        current_text = item.text()
                        item.setText(f"💀 {player_username} (DEAD)")
                        # Make it gray
                        item.setForeground(QtCore.Qt.gray)
                        break
                        
        elif header == 209:  # LEAVE_ROOM_RES
            if payload.get("status") == "success":
                self.toast_manager.success("Left room successfully")
                
                # Clear shared data
                self.window_manager.set_shared_data("current_room_id", None)
                self.window_manager.set_shared_data("current_room_name", None)
                self.window_manager.set_shared_data("is_host", False)
                
                # Navigate back to lobby
                self.window_manager.navigate_to("lobby")
            else:
                msg = payload.get("message", "Unknown error")
                self.toast_manager.error(f"Failed to leave room: {msg}")
                
        elif header == 302:  # GAME_START_RES_AND_ROLE
            if payload.get("status") == "success":
                
                # Show toast for game start
                self.toast_manager.success("🎮 Game Started!")
                
                # Disable buttons
                self.start_game_button.setEnabled(False)
                self.leave_room_button.setEnabled(False)
                
                # Show role card dialog (modal, 30s timer)
                role_card = RoleCardWindow(payload, self)
                role_card.exec_()  # Blocks until user closes or timer ends
                
                # After role card is closed
                # TODO: Navigate to game window or start night phase
                self.toast_manager.info("Night phase will begin...")
                
            else:
                msg = payload.get("message", "Unknown error")
                self.toast_manager.error(f"Failed to start game: {msg}")
    
    def on_logout(self):
        """Handle logout button click"""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout? You will leave the room.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                # Leave room first
                self.network_client.send_packet(208, {})  # LEAVE_ROOM_REQ
                
                # Send logout request
                self.network_client.send_packet(105, {})  # LOGOUT_REQ
                self.toast_manager.info("Logging out...")
                
                # Stop timer
                self.recv_timer.stop()
                
                # Clear shared data
                self.window_manager.set_shared_data("user_id", None)
                self.window_manager.set_shared_data("username", None)
                self.window_manager.set_shared_data("current_room_id", None)
                self.window_manager.set_shared_data("current_room_name", None)
                self.window_manager.set_shared_data("is_host", False)
                
                # Disconnect from server
                self.network_client.disconnect()
                
                # Navigate to welcome
                self.window_manager.navigate_to("welcome")
                
            except Exception as e:
                self.toast_manager.error(f"Logout error: {str(e)}")
