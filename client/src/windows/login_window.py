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
        self._pending_resume_room_id = None

        self.setObjectName("login_window")
        self.setup_ui()

        # Receive timer
        self.recv_timer = QtCore.QTimer()
        self.recv_timer.timeout.connect(self.receive_packets)

        # Connection monitor
        self.connection_monitor = None

        # Resume timeout
        self._resume_timeout_timer = QtCore.QTimer(self)
        self._resume_timeout_timer.setSingleShot(True)
        self._resume_timeout_timer.timeout.connect(self._on_resume_timeout)
        
    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)
        # Lấy client mạng từ dữ liệu chia sẻ
        self.network_client = self.window_manager.get_shared_data("network_client")
        connected = self.window_manager.get_shared_data("connected", False)
        if not self.network_client or not connected:
            # Avoid NoneType in on_login; require user to connect first.
            self.toast_manager.warning("Please connect to server first")
            self.window_manager.navigate_to("welcome")
            return

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

        if not self.network_client or not self.window_manager.get_shared_data("connected", False):
            self.toast_manager.warning("Not connected. Please connect again.")
            self.window_manager.navigate_to("welcome")
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
        
        # Mark disconnected but keep client instance so Welcome/ConnectionMonitor can reconnect
        self.window_manager.set_shared_data("connected", False)
        try:
            if self.network_client:
                self.network_client.disconnect()
        except Exception as e:
            print(f"[ERROR] Error during disconnect: {e}")
        
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
                self.window_manager.set_shared_data("spectator_mode", False)

                # Try resume (dead spectator) if we have a known room.
                resume_room_id = payload.get("resume_room_id")
                resume_room_status = payload.get("resume_room_status")
                resume_flag = self.window_manager.get_shared_data("resume_room_after_login", False)
                last_room_id = self.window_manager.get_shared_data("last_room_id")

                room_id_to_check = resume_room_id or (last_room_id if resume_flag else None)

                # Only auto-resume if the room is playing (or unknown status and user asked resume).
                should_try_resume = False
                if room_id_to_check:
                    if resume_room_status is None:
                        should_try_resume = True
                    else:
                        should_try_resume = int(resume_room_status) == 1

                if should_try_resume:
                    self._pending_resume_room_id = int(room_id_to_check)
                    self.window_manager.set_shared_data("resume_room_after_login", False)
                    self.toast_manager.info("Resuming ongoing game...")
                    try:
                        self.network_client.send_packet(210, {"room_id": self._pending_resume_room_id})  # GET_ROOM_INFO_REQ
                        self._resume_timeout_timer.start(2500)
                        # Keep recv_timer running to receive GET_ROOM_INFO_RES.
                        return
                    except Exception as e:
                        print(f"[WARNING] Failed to request room info for resume: {e}")
                        self._pending_resume_room_id = None

                # Default: stop receiving here and go to lobby
                self.recv_timer.stop()
                self.window_manager.navigate_to("lobby")
            else:
                msg = payload.get("message", "Unknown error")
                self.toast_manager.error(f"Login failed: {msg}")

        elif header == 211:  # GET_ROOM_INFO_RES
            if not self._pending_resume_room_id:
                return

            self._resume_timeout_timer.stop()
            pending_id = self._pending_resume_room_id
            self._pending_resume_room_id = None

            if payload.get("status") != "success":
                self.toast_manager.warning("Could not resume room. Going to lobby.")
                self.recv_timer.stop()
                self.window_manager.navigate_to("lobby")
                return

            room_status = payload.get("room_status")
            if room_status is None:
                room_status = payload.get("status")  # fallback if server older

            try:
                room_status_int = int(room_status)
            except Exception:
                room_status_int = 0

            if room_status_int != 1:
                # Not playing anymore
                self.recv_timer.stop()
                self.window_manager.navigate_to("lobby")
                return

            room_id = payload.get("room_id", pending_id)
            room_name = payload.get("room_name")
            players = payload.get("players", [])

            # Determine which phase screen to show.
            night_phase_active = False
            try:
                night_phase_active = int(payload.get("night_phase_active", 0)) != 0
            except Exception:
                night_phase_active = bool(payload.get("night_phase_active", False))

            role_card_active = False
            try:
                total = int(payload.get("role_card_total", 0))
                done = int(payload.get("role_card_done_count", 0))
                start_time = float(payload.get("role_card_start_time", 0))
                role_card_active = (total > 0 and done < total and start_time > 0)
            except Exception:
                role_card_active = False

            # Enter room as dead spectator
            self.window_manager.set_shared_data("current_room_id", room_id)
            self.window_manager.set_shared_data("current_room_name", room_name)
            self.window_manager.set_shared_data("room_players", players)
            self.window_manager.set_shared_data("is_host", False)
            self.window_manager.set_shared_data("spectator_mode", True)

            # Start RoomWindow in background so it can receive/dispatch packets,
            # without ever showing the Room window (avoid black Room window after resume).
            try:
                room_window = self.window_manager.windows.get("room")
                if room_window and hasattr(room_window, "activate_room_context"):
                    room_window.activate_room_context(start_receiving=True)
                    room_window.hide()
            except Exception as e:
                print(f"[WARNING] Failed to start RoomWindow in background: {e}")

            if role_card_active and not night_phase_active:
                # Players are still reading role cards; spectator just waits.
                self.window_manager.navigate_to("night_begin")
            elif night_phase_active:
                # Resume into the correct sub-phase screen like others.
                import time
                now = time.time()

                def _to_float(v):
                    try:
                        return float(v)
                    except Exception:
                        return 0.0

                seer_deadline = _to_float(payload.get("seer_deadline", 0))
                guard_deadline = _to_float(payload.get("guard_deadline", 0))
                wolf_deadline = _to_float(payload.get("wolf_deadline", 0))

                seer_remaining = max(0, int(seer_deadline - now)) if seer_deadline else 0
                guard_remaining = max(0, int(guard_deadline - now)) if guard_deadline else 0
                wolf_remaining = max(0, int(wolf_deadline - now)) if wolf_deadline else 0

                # Build players list as dicts (username/is_alive) for controller
                ctrl_players = []
                for p in players:
                    if isinstance(p, dict):
                        ctrl_players.append({
                            "username": p.get("username", ""),
                            "is_alive": p.get("is_alive", 1),
                        })

                from .night_phase_controller import NightPhaseController
                night_ctrl = NightPhaseController(
                    self.window_manager,
                    self.window_manager.get_shared_data("network_client"),
                    ctrl_players,
                    self.window_manager.get_shared_data("username"),
                    room_id,
                    False,
                    False,
                    False,
                    [],
                    seer_duration=max(1, seer_remaining) if seer_remaining else 30,
                    guard_duration=max(1, guard_remaining) if guard_remaining else 30,
                    wolf_duration=max(1, wolf_remaining) if wolf_remaining else 30,
                )
                self.window_manager.set_shared_data("night_phase_controller", night_ctrl)

                if seer_deadline and now < seer_deadline:
                    night_ctrl.seer_duration = max(1, seer_remaining)
                    night_ctrl.start_seer_phase()
                elif guard_deadline and now < guard_deadline:
                    night_ctrl.guard_duration = max(1, guard_remaining)
                    night_ctrl.start_guard_phase()
                elif wolf_deadline and now < wolf_deadline:
                    night_ctrl.wolf_duration = max(1, wolf_remaining)
                    night_ctrl.start_wolf_phase()
                else:
                    self.window_manager.navigate_to("day_chat")
            else:
                self.window_manager.navigate_to("day_chat")

            self.recv_timer.stop()

    def _on_resume_timeout(self):
        if not self._pending_resume_room_id:
            return
        self._pending_resume_room_id = None
        self.toast_manager.warning("Resume timed out. Going to lobby.")
        self.recv_timer.stop()
        self.window_manager.navigate_to("lobby")

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
