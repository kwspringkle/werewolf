from PyQt5 import QtWidgets, QtCore, QtGui
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.image_utils import set_window_icon
from components.user_header import UserHeader
from utils.connection_monitor import ConnectionMonitor


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
        self.current_host = None  # Lưu host hiện tại

        self.setObjectName("room_window")
        self.setup_ui()

        # Timer
        self.recv_timer = QtCore.QTimer()
        self.recv_timer.timeout.connect(self.receive_packets)

        # Connection monitor
        self.connection_monitor = None
        
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
        
        # Legend
        legend_layout = QtWidgets.QHBoxLayout()
        legend_label = QtWidgets.QLabel("👑 = Host  |  👤 = Player")
        legend_label.setStyleSheet("color: #FFD700; font-size: 11px; padding: 5px;")
        legend_layout.addWidget(legend_label)
        legend_layout.addStretch()
        players_layout.addLayout(legend_layout)
        
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
        
        # Lấy thông tin host từ room_players (player đầu tiên là host)
        players = self.window_manager.get_shared_data("room_players", [])
        if players:
            self.current_host = players[0].get("username")
        else:
            self.current_host = username if self.is_host else None
        
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
        self.update_player_list(players, username)
        self.current_player_count = len(players)
        self.update_player_count_ui()

        # Start receiving
        self.recv_timer.start(100)

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
        # KHÔNG dừng recv_timer khi hide - vẫn cần receive packets khi ở night_begin hoặc role_card
        # Chỉ dừng khi thực sự rời khỏi room (leave room, logout, etc.)
        # self.recv_timer.stop()  # Comment out để vẫn receive packets
        # Connection monitor vẫn chạy để monitor connection
        
    def update_player_list(self, players, current_username):
        """Cập nhật widget danh sách người chơi"""
        self.player_list.clear()
        
        # Player đầu tiên là host
        for i, player in enumerate(players):
            username = player.get("username", "Unknown")
            is_host = (i == 0) or (username == self.current_host)
            is_me = (username == current_username)
            
            # Build text
            if is_host:
                icon = "👑"
                role_text = "HOST"
            else:
                icon = "👤"
                role_text = "PLAYER"
            
            me_marker = " (You)" if is_me else ""
            display_text = f"{icon} {username}{me_marker} - {role_text}"
            
            item = QtWidgets.QListWidgetItem(display_text)
            
            # Color coding
            if is_host:
                item.setForeground(QtGui.QColor("#FFD700"))  # Gold for host
            else:
                item.setForeground(QtGui.QColor("#FFFFFF"))  # White for player
            
            self.player_list.addItem(item)
                
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
            
    def rebuild_player_list_from_ui(self):
        """Rebuild player list với host mới"""
        my_username = self.window_manager.get_shared_data("username")
        
        # Collect all current players from UI
        players = []
        for i in range(self.player_list.count()):
            item_text = self.player_list.item(i).text()
            # Extract username: remove icons and markers
            username = item_text.replace("👑", "").replace("👤", "")
            username = username.split(" (You)")[0].split(" - ")[0].strip()
            
            if username:
                players.append({"username": username})
        
        # Reorder: new host first, others follow
        if self.current_host:
            host_player = None
            other_players = []
            
            for p in players:
                if p["username"] == self.current_host:
                    host_player = p
                else:
                    other_players.append(p)
            
            if host_player:
                players = [host_player] + other_players
        
        # Rebuild UI with correct icons and colors
        self.update_player_list(players, my_username)
    
    def on_leave_room(self):
        """Xử lý khi nhấn nút rời phòng"""
        try:
            self.network_client.send_packet(208, {})  # LEAVE_ROOM_REQ
        except Exception as e:
            self.toast_manager.error(f"Failed to leave room: {str(e)}")
            
    def receive_packets(self):
        """Nhận gói tin từ server"""
        if not self.network_client:
            return
            
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
                # Chỉ handle disconnect nếu thực sự disconnect, không phải timeout
                if self.recv_timer.isActive():
                    self.handle_server_disconnect()
            else:
                # Không hiển thị error cho mọi exception - có thể chỉ là timeout
                print(f"[DEBUG] Receive error (non-critical): {error_msg}")
        except ConnectionError as e:
            # Connection lost detected
            print(f"[DEBUG] Connection lost: {e}")
            # Trigger connection lost handling via monitor
            if self.connection_monitor:
                self.connection_monitor.is_connected = False
                self.connection_monitor.stop()
                self.connection_monitor.handle_connection_lost()
        except Exception as e:
            # Catch all other exceptions để tránh crash
            print(f"[WARNING] Unexpected error in receive_packets: {e}")
            import traceback
            traceback.print_exc()
            
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
        self.window_manager.set_shared_data("user_id", None)
        self.window_manager.set_shared_data("username", None)
        self.window_manager.set_shared_data("current_room_id", None)
        self.window_manager.set_shared_data("current_room_name", None)
        self.window_manager.set_shared_data("is_host", False)
        self.window_manager.set_shared_data("network_client", None)
        
        # Navigate về welcome screen
        self.window_manager.navigate_to("welcome")
            
    def handle_packet(self, header, payload):
        """Xử lý gói tin nhận được"""
        # Handle PING from server
        if header == 501:  # PING
            try:
                # Reply with proper PONG header (502). Payload is kept for compatibility/logging.
                self.network_client.send_packet(502, {"type": "pong"})
                if self.connection_monitor:
                    self.connection_monitor.on_pong_received()
            except:
                pass
            return

        # CHAT_BROADCAST (centralized receive to avoid multiple windows stealing packets)
        if header == 402:  # CHAT_BROADCAST
            try:
                chat_type = payload.get("chat_type", "day") if isinstance(payload, dict) else "day"

                if chat_type == "wolf":
                    night_ctrl = self.window_manager.get_shared_data("night_phase_controller")
                    wolf_chat = getattr(night_ctrl, "wolf_chat_window", None) if night_ctrl else None
                    if wolf_chat and hasattr(wolf_chat, "handle_chat_broadcast"):
                        wolf_chat.handle_chat_broadcast(payload)
                else:
                    day_chat = self.window_manager.windows.get("day_chat") if hasattr(self.window_manager, "windows") else None
                    if day_chat and hasattr(day_chat, "handle_chat_broadcast"):
                        day_chat.handle_chat_broadcast(payload)
            except Exception as e:
                print(f"[WARNING] Failed to dispatch CHAT_BROADCAST: {e}")
            return

        username = self.window_manager.get_shared_data("username")
        # Guard protect response - this shouldn't trigger night phase start
        # Night phase should start from PHASE_NIGHT (303) packet
        if header == 407:  # GUARD_PROTECT_REQ (this is wrong - 407 is request, should be response)
            # Actually this seems wrong - 407 is GUARD_PROTECT_REQ from protocol.h
            # This handler should probably be removed or handle something else
            pass

        if header == 408:  # GUARD_PROTECT_RES
            # Optionally handle guard result/confirmation here (e.g., show toast)
            status = payload.get("status")
            if status == "success":
                self.toast_manager.success("Guard action sent!")
            else:
                msg = payload.get("message", "Guard action failed")
                self.toast_manager.warning(msg)
            return
        
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
                new_host = payload.get("new_host")  # Server gửi host mới nếu có
                self.current_player_count = current
                
                self.toast_manager.warning(f"{player_username} left ({current} players)")
                
                # Remove from list
                for i in range(self.player_list.count()):
                    if player_username in self.player_list.item(i).text():
                        self.player_list.takeItem(i)
                        break
                
                # Check if host changed
                if new_host and new_host != self.current_host:
                    old_host = self.current_host
                    self.current_host = new_host
                    my_username = self.window_manager.get_shared_data("username")
                    
                    if new_host == my_username:
                        # I became host
                        self.is_host = True
                        self.window_manager.set_shared_data("is_host", True)
                        self.toast_manager.success(f"👑 You are now the room host!")
                        
                        # Update UI
                        self.start_game_button.setVisible(True)
                        self.room_info_label.setText(f"Room ID: {self.current_room_id} - You are HOST 👑")
                    else:
                        # Someone else became host
                        self.toast_manager.info(f"👑 {new_host} is now the room host")
                    
                    # Rebuild player list với host mới
                    self.rebuild_player_list_from_ui()
                
                # Update UI
                self.update_player_count_ui()
                
                # Extra warning for host if below minimum
                if self.is_host and current < self.MIN_PLAYERS:
                    needed = self.MIN_PLAYERS - current
                    self.toast_manager.warning(f"⚠️ Need {needed} more player{'s' if needed > 1 else ''} to start!")
                    
            elif update_type == "player_disconnected":
                player_username = payload.get("username")
                game_started = payload.get("game_started", False)
                
                if game_started:
                    # Sau khi game start: mark as dead
                    self.toast_manager.error(f"💀 {player_username} disconnected - Marked as DEAD")
                    
                    # Mark player as dead in list
                    for i in range(self.player_list.count()):
                        item = self.player_list.item(i)
                        if player_username in item.text() and "💀" not in item.text():
                            item.setText(f"💀 {player_username} (DEAD)")
                            item.setForeground(QtGui.QColor("#555555"))  # Gray
                            break
                else:
                    # Trước khi game start: treat như player_left
                    current = payload.get("current_players", 0)
                    self.current_player_count = current
                    
                    self.toast_manager.warning(f"{player_username} disconnected ({current} players)")
                    
                    # Remove from list
                    for i in range(self.player_list.count()):
                        if player_username in self.player_list.item(i).text():
                            self.player_list.takeItem(i)
                            break
                    
                    # Check if host changed
                    new_host = payload.get("new_host")
                    if new_host and new_host != self.current_host:
                        self.current_host = new_host
                        my_username = self.window_manager.get_shared_data("username")
                        
                        if new_host == my_username:
                            self.is_host = True
                            self.window_manager.set_shared_data("is_host", True)
                            self.toast_manager.success(f"👑 You are now the room host!")
                            self.start_game_button.setVisible(True)
                            self.room_info_label.setText(f"Room ID: {self.current_room_id} - You are HOST 👑")
                        else:
                            self.toast_manager.info(f"👑 {new_host} is now the room host")
                        
                        # Rebuild player list với host mới
                        self.rebuild_player_list_from_ui()
                    
                    # Update UI
                    self.update_player_count_ui()
                    
                    if self.is_host and current < self.MIN_PLAYERS:
                        needed = self.MIN_PLAYERS - current
                        self.toast_manager.warning(f"⚠️ Need {needed} more player{'s' if needed > 1 else ''} to start!")
                        
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
                print("[DEBUG] Game Started! Received role assignment")
                
                # Show toast for game start
                self.toast_manager.success("🎮 Game Started!")
                
                # Disable buttons
                self.start_game_button.setEnabled(False)
                self.leave_room_button.setEnabled(False)
                
                # Save role info for later (used during night)
                self.window_manager.set_shared_data("role_info", payload)

                # Navigate to role card window
                # Role card window will send ROLE_CARD_DONE_REQ when ready/timer expires
                # and then navigate to night_begin window
                self.window_manager.navigate_to("role_card")
                
            else:
                msg = payload.get("message", "Unknown error")
                self.toast_manager.error(f"Failed to start game: {msg}")
        elif header == 303:  # PHASE_NIGHT
            print("[DEBUG] Received PHASE_NIGHT from server, starting night phase")
            # payload may contain duration và các phase duration riêng
            duration = payload.get("duration", 90)  # Total duration (seer + guard + wolf)
            seer_duration = payload.get("seer_duration", 30)
            guard_duration = payload.get("guard_duration", 30)
            wolf_duration = payload.get("wolf_duration", 30)
            print(f"[DEBUG] Phase durations - seer: {seer_duration}s, guard: {guard_duration}s, wolf: {wolf_duration}s, total: {duration}s")
            
            # Lấy players list từ server (đảm bảo tất cả clients có cùng players list)
            players_from_server = payload.get("players", [])
            if players_from_server:
                # Update room_players trong shared_data với players list từ server
                # Đảm bảo tất cả clients có cùng players list
                self.window_manager.set_shared_data("room_players", players_from_server)
                print(f"[DEBUG] Updated room_players from server: {len(players_from_server)} players")
                print(f"[DEBUG] Players from server: {[p.get('username', 'unknown') for p in players_from_server]}")
            else:
                print(f"[WARNING] No players list in PHASE_NIGHT packet, using existing room_players")
            
            # Đóng tất cả các window có thể đang mở (role_card, night_begin)
            # Đảm bảo đóng đúng cách để tránh window trắng
            if "night_begin" in self.window_manager.windows:
                night_begin_win = self.window_manager.windows["night_begin"]
                if night_begin_win.isVisible():
                    print(f"[DEBUG] Closing night_begin_window, starting night phase")
                    night_begin_win.hide()
                    if hasattr(night_begin_win, 'timer') and night_begin_win.timer:
                        night_begin_win.timer.stop()
            
            if "role_card" in self.window_manager.windows:
                role_card_win = self.window_manager.windows["role_card"]
                if role_card_win.isVisible():
                    print(f"[DEBUG] Closing role_card_window, starting night phase")
                    role_card_win.hide()
            
            # Bắt đầu night phase ngay (sẽ show seer select hoặc seer wait)
            self.start_night_phase(duration, seer_duration, guard_duration, wolf_duration)

        # NOTE: PING/PONG handled at the top of this function to avoid duplicate branches.
        elif header == 406:  # SEER_RESULT
            # Only the seer will receive this normally
            status = payload.get("status")
            if status == "success":
                target = payload.get("target_username")
                is_wolf = bool(payload.get("is_werewolf"))
                # Get night phase controller from shared data
                night_ctrl = self.window_manager.get_shared_data("night_phase_controller")
                if night_ctrl:
                    night_ctrl.handle_seer_result(target, is_wolf)
                else:
                    print("[ERROR] Night phase controller not found when receiving SEER_RESULT")
                    self.toast_manager.warning("Error: Night phase controller not initialized")
            else:
                msg = payload.get("message", "Seer check failed")
                self.toast_manager.warning(msg)

        elif header == 404:  # WOLF_KILL_RES (vote received confirmation)
            if isinstance(payload, dict) and payload.get("type") == "wolf_vote_received":
                try:
                    self.toast_manager.success("✅ Wolf vote submitted!")
                except Exception:
                    pass
            else:
                print(f"[DEBUG] Received WOLF_KILL_RES (404): {payload}")
        
        elif header == 311:  # PHASE_GUARD_START
            # Server báo tất cả client chuyển sang guard phase
            print("[DEBUG] Received PHASE_GUARD_START from server, moving to guard phase")
            guard_duration = payload.get("guard_duration", 30)
            
            # Get night phase controller from shared data
            night_ctrl = self.window_manager.get_shared_data("night_phase_controller")
            if night_ctrl:
                # Không cần update players list - giữ nguyên từ khi start_night_phase
                # players list đã được set đúng khi start_night_phase với đầy đủ thông tin
                print(f"[DEBUG] Guard phase - using existing players list: {len(night_ctrl.players)} players")
                print(f"[DEBUG] Players usernames: {[p.get('username', 'unknown') if isinstance(p, dict) else str(p) for p in night_ctrl.players]}")
                
                # Update guard duration if needed
                night_ctrl.guard_duration = guard_duration
                # Chuyển sang guard phase - guard sẽ thấy GuardSelectWindow, còn lại thấy GuardWaitWindow
                night_ctrl.start_guard_phase()
            else:
                print("[ERROR] Night phase controller not found when receiving PHASE_GUARD_START")
                self.toast_manager.warning("Error: Night phase controller not initialized")
        
        elif header == 312:  # PHASE_WOLF_START
            # Server báo tất cả client chuyển sang wolf phase
            print("[DEBUG] Received PHASE_WOLF_START from server, moving to wolf phase")
            wolf_duration = payload.get("wolf_duration", 30)
            
            # Get night phase controller from shared data
            night_ctrl = self.window_manager.get_shared_data("night_phase_controller")
            if night_ctrl:
                # Không cần update players list - giữ nguyên từ khi start_night_phase
                # players list đã được set đúng khi start_night_phase với đầy đủ thông tin
                print(f"[DEBUG] Wolf phase - using existing players list: {len(night_ctrl.players)} players")
                print(f"[DEBUG] Players usernames: {[p.get('username', 'unknown') if isinstance(p, dict) else str(p) for p in night_ctrl.players]}")
                
                # Re-check role info to ensure is_wolf is correct
                role_info = self.window_manager.get_shared_data("role_info", {})
                role_num = role_info.get("role", 0)
                is_wolf = (role_num == 1)
                # Update is_wolf in night_ctrl to ensure correct detection
                night_ctrl.is_wolf = is_wolf
                # Also update wolf_usernames from role_info
                wolf_usernames = role_info.get("werewolf_team", [])
                if not wolf_usernames:
                    # Fallback: check role in players list
                    wolf_usernames = [p.get("username") for p in night_ctrl.players if p.get("role") == 1]
                night_ctrl.wolf_usernames = wolf_usernames
                
                print(f"[DEBUG] Updated wolf info - is_wolf: {is_wolf}, wolf_usernames: {wolf_usernames}")
                print(f"[DEBUG] All players in room: {[p.get('username', 'unknown') if isinstance(p, dict) else str(p) for p in night_ctrl.players]}")
                
                # Update wolf duration if needed
                night_ctrl.wolf_duration = wolf_duration
                # Chuyển sang wolf phase - wolf sẽ thấy WolfSelectWindow/WolfChatWindow, còn lại thấy wait window
                night_ctrl.start_wolf_phase()
            else:
                print("[ERROR] Night phase controller not found when receiving PHASE_WOLF_START")
                self.toast_manager.warning("Error: Night phase controller not initialized")
        
        elif header == 304:  # PHASE_DAY
            # Server báo bắt đầu day phase sau khi night phase kết thúc
            print("[DEBUG] Received PHASE_DAY from server, starting day phase")
            
            # Payload compact (mới): { result: "killed"|"no_kill", targetId? }
            # Payload legacy (cũ): { dead_players: [...] }
            dead_players = []
            if isinstance(payload, dict) and "result" in payload:
                result = payload.get("result")
                target = payload.get("targetId") or payload.get("target_username")
                if result == "killed" and target:
                    dead_players = [target]
                print(f"[DEBUG] PHASE_DAY compact result: {result}, target={target}")
            else:
                dead_players = payload.get("dead_players", [])
                print(f"[DEBUG] Dead players (legacy): {dead_players}")
            
            # Đóng tất cả các window của night phase
            night_ctrl = self.window_manager.get_shared_data("night_phase_controller")
            if night_ctrl:
                # Close all night phase windows - đóng đúng cách để tránh crash
                try:
                    if hasattr(night_ctrl, 'seer_window') and night_ctrl.seer_window:
                        if night_ctrl.seer_window.isVisible():
                            night_ctrl.seer_window.hide()
                            night_ctrl.seer_window.close()
                except Exception as e:
                    print(f"[WARNING] Error closing seer_window: {e}")
                
                try:
                    if hasattr(night_ctrl, 'seer_result_window') and night_ctrl.seer_result_window:
                        if night_ctrl.seer_result_window.isVisible():
                            night_ctrl.seer_result_window.hide()
                            night_ctrl.seer_result_window.close()
                except Exception as e:
                    print(f"[WARNING] Error closing seer_result_window: {e}")
                
                try:
                    if hasattr(night_ctrl, 'guard_window') and night_ctrl.guard_window:
                        if night_ctrl.guard_window.isVisible():
                            night_ctrl.guard_window.hide()
                            night_ctrl.guard_window.close()
                except Exception as e:
                    print(f"[WARNING] Error closing guard_window: {e}")
                
                try:
                    if hasattr(night_ctrl, 'wolf_controller') and night_ctrl.wolf_controller:
                        if night_ctrl.wolf_controller.isVisible():
                            night_ctrl.wolf_controller.hide()
                            night_ctrl.wolf_controller.close()
                except Exception as e:
                    print(f"[WARNING] Error closing wolf_controller: {e}")
            
            # Hiển thị death announcement window
            if "death_announcement" in self.window_manager.windows:
                death_window = self.window_manager.windows["death_announcement"]
                death_window.set_dead_players(dead_players)
                # Use WindowManager so countdown can auto-navigate to day chat and auto-hide this screen.
                self.window_manager.navigate_to("death_announcement")
            else:
                print("[ERROR] Death announcement window not registered")
                # Fallback: navigate directly to day chat
                self.window_manager.navigate_to("day_chat")
    
    def start_night_phase(self, duration, seer_duration=30, guard_duration=30, wolf_duration=30):
        """Bắt đầu night phase (được gọi khi nhận PHASE_NIGHT từ server)"""
        print(f"[DEBUG] Starting night phase - total: {duration}s, seer: {seer_duration}s, guard: {guard_duration}s, wolf: {wolf_duration}s")
        
        # Đảm bảo đóng tất cả các window có thể che mất seer window
        # Đóng tất cả windows trong window_manager
        if "night_begin" in self.window_manager.windows:
            night_begin_win = self.window_manager.windows["night_begin"]
            if night_begin_win.isVisible():
                print(f"[DEBUG] Force closing night_begin_window before starting night phase")
                night_begin_win.hide()
                if hasattr(night_begin_win, 'timer') and night_begin_win.timer:
                    night_begin_win.timer.stop()
        
        if "role_card" in self.window_manager.windows:
            role_card_win = self.window_manager.windows["role_card"]
            if role_card_win.isVisible():
                print(f"[DEBUG] Force closing role_card_window before starting night phase")
                role_card_win.hide()
        
        # Lấy lại các thông tin cần thiết
        role_info = self.window_manager.get_shared_data("role_info", {})
        # Server sends role as number: 0=VILLAGER, 1=WEREWOLF, 2=SEER, 3=GUARD
        role_num = role_info.get("role", 0)
        is_seer = (role_num == 2)
        is_guard = (role_num == 3)
        is_wolf = (role_num == 1)
        
        # Lấy players list từ shared_data (đã được update từ PHASE_NIGHT packet)
        players_raw = self.window_manager.get_shared_data("room_players", [])
        my_username = self.window_manager.get_shared_data("username")
        room_id = self.window_manager.get_shared_data("current_room_id")
        
        # Đảm bảo players có đầy đủ thông tin: username và is_alive
        # Players list từ server đã có is_alive, chỉ cần normalize format
        players = []
        for p in players_raw:
            if isinstance(p, dict):
                # Đảm bảo có username và is_alive
                player_info = {
                    "username": p.get("username", ""),
                    "is_alive": p.get("is_alive", 1),  # Server gửi is_alive, mặc định 1 nếu không có
                    "role": p.get("role", None)  # Giữ role nếu có
                }
            else:
                # Nếu p là string (username) - fallback
                player_info = {
                    "username": str(p),
                    "is_alive": 1,  # Mặc định là alive
                    "role": None
                }
            players.append(player_info)
        
        # Debug: Print players list
        print(f"[DEBUG] start_night_phase - players count: {len(players)}")
        print(f"[DEBUG] start_night_phase - players: {players}")
        print(f"[DEBUG] start_night_phase - all players usernames: {[p.get('username', 'unknown') for p in players]}")
        
        # Get wolf usernames from werewolf team if available, otherwise check role
        wolf_usernames = role_info.get("werewolf_team", [])
        if not wolf_usernames:
            # Fallback: check role in players list (though this might not work if role not exposed)
            wolf_usernames = [p["username"] for p in players if p.get("role") == 1]
        
        print(f"[DEBUG] Player role - is_seer: {is_seer}, is_guard: {is_guard}, is_wolf: {is_wolf}")
        
        from .night_phase_controller import NightPhaseController
        night_ctrl = NightPhaseController(
            self.window_manager, self.network_client, players, my_username, room_id,
            is_seer, is_guard, is_wolf, wolf_usernames, 
            seer_duration, guard_duration, wolf_duration
        )
        # Store night controller in window_manager so SEER_RESULT can access it
        self.window_manager.set_shared_data("night_phase_controller", night_ctrl)
        
        # Start night phase - this will show seer window immediately
        print("[DEBUG] Calling night_ctrl.start() to show seer window...")
        night_ctrl.start()
        print("[DEBUG] night_ctrl.start() completed")
    
    def on_connection_lost(self):
        """Handle connection lost"""
        self.recv_timer.stop()

    def on_connection_restored(self):
        """Handle connection restored after reconnect"""
        print("[DEBUG] Room: Connection restored, navigating to login")
        # Stop timer
        self.recv_timer.stop()

        # Clear session and room data
        self.window_manager.set_shared_data("user_id", None)
        self.window_manager.set_shared_data("username", None)
        self.window_manager.set_shared_data("current_room_id", None)
        self.window_manager.set_shared_data("current_room_name", None)
        self.window_manager.set_shared_data("is_host", False)

        # Navigate to login screen
        self.window_manager.navigate_to("login")

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
