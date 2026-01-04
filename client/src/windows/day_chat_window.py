from PyQt5 import QtWidgets, QtCore
from components.user_header import UserHeader
from utils.image_utils import set_window_icon

class DayChatWindow(QtWidgets.QWidget):
    """Day phase chat window - tất cả người chơi có thể chat"""
    def __init__(self, toast_manager=None, window_manager=None):
        super().__init__()
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.network_client = None
        self.current_room_id = None
        self.my_username = None
        
        self.setObjectName("day_chat_window")
        self.setWindowTitle("Werewolf - Day Phase")
        self.setup_ui()
        # IMPORTANT: Do NOT read from network socket here.
        # RoomWindow is the single consumer of packets and will dispatch CHAT_BROADCAST to this window.
        
    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)

        # Get shared data
        self.network_client = self.window_manager.get_shared_data("network_client")
        self.current_room_id = self.window_manager.get_shared_data("current_room_id")
        self.my_username = self.window_manager.get_shared_data("username")

        print(f"[DEBUG] DayChatWindow shown - network_client: {self.network_client is not None}, room_id: {self.current_room_id}, username: {self.my_username}")

        # Set username in header
        if self.my_username:
            self.user_header.set_username(self.my_username)

        # Packets are received by RoomWindow; this window only renders chat UI.

        # Add a welcome message to show chat is working
        QtCore.QTimer.singleShot(100, lambda: self.append_message("System", "Day phase started. Discuss who might be a werewolf!"))

        # Force focus on input box after window is shown
        def set_input_focus():
            print(f"[DEBUG] Setting focus on input box - enabled: {self.input_box.isEnabled()}, visible: {self.input_box.isVisible()}")
            self.input_box.setFocus()
            print(f"[DEBUG] Input box has focus: {self.input_box.hasFocus()}")
        QtCore.QTimer.singleShot(200, set_input_focus)
        
    def hideEvent(self, event):
        """Called when window is hidden"""
        super().hideEvent(event)
        # No socket receive loop here.

    def handle_chat_broadcast(self, payload: dict):
        """Called by RoomWindow when receiving CHAT_BROADCAST (402)."""
        if not isinstance(payload, dict):
            return
        chat_type = payload.get("chat_type", "day")
        if chat_type != "day":
            return
        username = payload.get("username", "Unknown")
        message = payload.get("message", "")
        self.append_message(username, message)
        
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        self.setWindowTitle("Werewolf - Day Phase")
        self.resize(800, 700)
        
        set_window_icon(self)
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # User header (username + logout)
        self.user_header = UserHeader(self)
        self.user_header.logout_clicked.connect(self.on_logout)
        main_layout.addWidget(self.user_header)
        
        # Header
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addStretch()
        
        sun_icon = QtWidgets.QLabel("☀️")
        sun_icon.setStyleSheet("font-size: 40px;")
        header_layout.addWidget(sun_icon)
        
        # Title
        title_label = QtWidgets.QLabel("DAY PHASE")
        title_label.setObjectName("day_title_label")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 28px;
            color: #f39c12;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(title_label)
        
        sun_icon2 = QtWidgets.QLabel("☀️")
        sun_icon2.setStyleSheet("font-size: 40px;")
        header_layout.addWidget(sun_icon2)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Subtitle
        subtitle = QtWidgets.QLabel("Discuss and vote to eliminate the werewolves!")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #cccccc; margin-bottom: 10px;")
        main_layout.addWidget(subtitle)
        
        # Chat area
        chat_group = QtWidgets.QGroupBox("Chat")
        chat_group.setObjectName("chat_group")
        chat_group.setStyleSheet("""
            QGroupBox#chat_group {
                border: 2px solid #f39c12;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 16px;
                font-weight: bold;
                color: #f39c12;
            }
        """)
        chat_layout = QtWidgets.QVBoxLayout()
        
        # Messages area
        self.messages_area = QtWidgets.QScrollArea()
        self.messages_area.setWidgetResizable(True)
        self.messages_area.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.messages_area.setMinimumHeight(300)  # Ensure chat area is visible
        self.messages_area.setStyleSheet("""
            QScrollArea {
                background-color: #0f1a2e;
                border: 1px solid #0f3460;
                border-radius: 8px;
            }
        """)
        
        self.messages_container = QtWidgets.QWidget()
        self.messages_container.setStyleSheet("background: #0f1a2e;")
        self.messages_layout = QtWidgets.QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()
        self.messages_area.setWidget(self.messages_container)
        chat_layout.addWidget(self.messages_area, 1)
        
        # Input row
        input_layout = QtWidgets.QHBoxLayout()
        self.input_box = QtWidgets.QLineEdit()
        self.input_box.setPlaceholderText("Type a message...")
        self.input_box.setStyleSheet("""
            QLineEdit {
                background: #0f1a2e;
                border: 1px solid #0f3460;
                color: #eaeaea;
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #f39c12;
            }
        """)
        self.input_box.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_box)
        
        self.send_btn = QtWidgets.QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: black;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
                padding: 10px 20px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3fe07a;
            }
            QPushButton:pressed {
                background-color: #23b45a;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        self.input_box.textChanged.connect(lambda t: self.send_btn.setEnabled(bool(t.strip())))
        
        chat_layout.addLayout(input_layout)
        chat_group.setLayout(chat_layout)
        main_layout.addWidget(chat_group, 1)
        
    def send_message(self):
        """Gửi tin nhắn chat"""
        msg = self.input_box.text().strip()

        if not msg:
            print("[DEBUG] Day chat: Empty message")
            return

        if not self.network_client:
            print("[ERROR] Day chat: network_client is None!")
            if self.toast_manager:
                self.toast_manager.error("Network client not available")
            return

        if not self.current_room_id:
            print("[ERROR] Day chat: current_room_id is None!")
            if self.toast_manager:
                self.toast_manager.error("Room ID not available")
            return

        try:
            payload = {
                "room_id": self.current_room_id,
                "message": msg
            }
            print(f"[DEBUG] Sending day chat message: {msg} to room {self.current_room_id}")
            self.network_client.send_packet(401, payload)  # CHAT_REQ
            self.input_box.clear()
        except Exception as e:
            print(f"[ERROR] Failed to send day chat: {e}")
            if self.toast_manager:
                self.toast_manager.error(f"Failed to send message: {str(e)}")
    
    def append_message(self, username, msg):
        """Thêm tin nhắn vào chat"""
        def _esc(text):
            return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
        
        safe_user = _esc(username if username is not None else "")
        safe_msg = _esc(msg if msg is not None else "")
        
        is_self = (username == self.my_username)
        
        # Message frame
        msg_frame = QtWidgets.QFrame()
        msg_frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        v = QtWidgets.QVBoxLayout(msg_frame)
        v.setContentsMargins(6, 2, 6, 2)
        v.setSpacing(4)
        
        user_lbl = QtWidgets.QLabel(safe_user if not is_self else "me")
        user_lbl.setStyleSheet("font-size:11px; color:rgba(255,255,255,0.75);")
        v.addWidget(user_lbl, alignment=QtCore.Qt.AlignLeft if not is_self else QtCore.Qt.AlignRight)
        
        bubble = QtWidgets.QLabel(safe_msg)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        bubble.setContentsMargins(10, 8, 10, 8)
        bubble.setMaximumWidth(500)
        if is_self:
            bubble.setStyleSheet("background:#2ecc71; color:#062b1a; padding:8px; border-radius:12px;")
        else:
            bubble.setStyleSheet("background:#3498db; color:white; padding:8px; border-radius:12px;")
        v.addWidget(bubble, alignment=QtCore.Qt.AlignLeft if not is_self else QtCore.Qt.AlignRight)
        
        # Wrap into hbox to align left or right
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if is_self:
            row.addStretch()
            row.addWidget(msg_frame)
        else:
            row.addWidget(msg_frame)
            row.addStretch()
        
        # Insert just before the stretch spacer
        self.messages_layout.insertLayout(self.messages_layout.count()-1, row)
        
        # Auto-scroll to bottom
        QtCore.QTimer.singleShot(50, lambda: self.messages_area.verticalScrollBar().setValue(
            self.messages_area.verticalScrollBar().maximum()
        ))
    
    def receive_packets(self):
        """Nhận gói tin từ server"""
        if not self.network_client:
            print("[DEBUG] Day chat: network_client is None in receive_packets")
            return

        try:
            header, payload = self.network_client.receive_packet()

            if header is None:
                return

            print(f"[DEBUG] Day chat received packet: header={header}, payload={payload}")
            self.handle_packet(header, payload)
            
        except RuntimeError as e:
            error_msg = str(e)
            if "Server closed" in error_msg or "Receive failed" in error_msg:
                print(f"[ERROR] Server disconnected: {error_msg}")
                if self.toast_manager:
                    self.toast_manager.error("⚠️ Server disconnected!")
            else:
                if self.toast_manager:
                    self.toast_manager.error(f"Receive error: {error_msg}")
        except ConnectionError as e:
            print(f"[DEBUG] Connection lost: {e}")
            if self.toast_manager:
                self.toast_manager.error("⚠️ Connection lost!")
    
    def handle_packet(self, header, payload):
        """Xử lý gói tin nhận được"""
        # Handle PING
        if header == 501:  # PING
            try:
                self.network_client.send_packet(502, {"type": "pong"})
            except:
                pass
            return
        
        # Handle CHAT_BROADCAST
        if header == 402:  # CHAT_BROADCAST
            chat_type = payload.get("chat_type", "day")
            print(f"[DEBUG] Day chat received CHAT_BROADCAST with type: {chat_type}")
            # Only show day chat messages, ignore wolf chat
            if chat_type == "day":
                username = payload.get("username", "Unknown")
                message = payload.get("message", "")
                print(f"[DEBUG] Day chat displaying message from {username}: {message}")
                self.append_message(username, message)
            else:
                print(f"[DEBUG] Day chat ignoring {chat_type} message")
            return
    
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
                if self.network_client:
                    self.network_client.send_packet(105, {})  # LOGOUT_REQ
                
                if self.toast_manager:
                    self.toast_manager.info("Logging out...")
                
                # Stop timer
                self.recv_timer.stop()
                
                # Clear shared data
                if self.window_manager:
                    self.window_manager.set_shared_data("user_id", None)
                    self.window_manager.set_shared_data("username", None)
                    self.window_manager.set_shared_data("current_room_id", None)
                    self.window_manager.set_shared_data("current_room_name", None)
                    self.window_manager.set_shared_data("is_host", False)
                
                # Disconnect from server
                if self.network_client:
                    self.network_client.disconnect()
                
                # Navigate to welcome
                if self.window_manager:
                    self.window_manager.navigate_to("welcome")
                    
            except Exception as e:
                if self.toast_manager:
                    self.toast_manager.error(f"Logout error: {str(e)}")

