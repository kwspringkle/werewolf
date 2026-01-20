from PyQt5 import QtWidgets, QtCore
from components.user_header import UserHeader
import time
class WolfChatWindow(QtWidgets.QWidget):
    """Styled wolf chat (card-like, timer)"""
    def __init__(self, my_username, wolf_usernames, send_callback=None, duration_seconds=30, network_client=None, room_id=None, parent=None, window_manager=None, toast_manager=None, deadline=None):
        super().__init__(parent)
        self.use_default_size = True
        self.preserve_window_flags = False
        self.setObjectName("wolf_chat_window")
        self.setWindowTitle("Wolf Chat")
        self.send_callback = send_callback
        self.my_username = my_username
        self.wolf_usernames = wolf_usernames
        self.duration = duration_seconds
        # Sử dụng deadline từ server (epoch seconds) để đồng bộ thời gian chính xác
        self.deadline = deadline
        if self.deadline is None:
            # Fallback: tính từ duration
            self.deadline = time.time() + duration_seconds
        # Tính remaining từ deadline
        self.remaining = max(0, int(self.deadline - time.time()))
        self.network_client = network_client
        self.room_id = room_id
        self.window_manager = window_manager
        self.toast_manager = toast_manager
        self.can_send_chat = True
        self.setup_ui()
        self.start_timer()
        # IMPORTANT: Do NOT read from network socket here.
        # RoomWindow is the single consumer of packets and will dispatch CHAT_BROADCAST to this window.

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.user_header = UserHeader(self)
        self.user_header.set_username(self.my_username or "Player")
        self.user_header.logout_clicked.connect(self.on_logout)
        main_layout.addWidget(self.user_header)

        card = QtWidgets.QFrame()
        card.setObjectName("wolf_chat_card")
        card.setStyleSheet("""
            QFrame#wolf_chat_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 3px solid #e94560;
                border-radius: 15px;
            }
        """)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(15)
        card_layout.setContentsMargins(30, 30, 30, 30)

        self.timer_label = QtWidgets.QLabel(f"⏱️ {self.remaining}s")
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 18px; color: #f39c12; font-weight: bold; background-color: rgba(243,156,18,0.1); padding:8px; border-radius:5px;")
        card_layout.addWidget(self.timer_label)

        # Header with icon and back button so button is always visible
        header_h = QtWidgets.QHBoxLayout()
        icon_label = QtWidgets.QLabel("🐺")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 60px;")
        header_h.addWidget(icon_label)

        title = QtWidgets.QLabel("Wolf Chat")
        title.setStyleSheet("font-size:18px; font-weight:bold; color:#eaeaea;")
        header_h.addWidget(title)
        header_h.addStretch()

        self.switch_btn = QtWidgets.QPushButton("Back to vote")
        self.switch_btn.setMinimumHeight(28)
        self.switch_btn.setStyleSheet("""
            QPushButton {
                background-color: #e94560;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #ff5770;
            }
            QPushButton:pressed {
                background-color: #d03550;
            }
        """)
        header_h.addWidget(self.switch_btn)
        card_layout.addLayout(header_h)

        # Participants label
        participants = QtWidgets.QLabel("Wolves: " + ", ".join(self.wolf_usernames))
        participants.setAlignment(QtCore.Qt.AlignCenter)
        participants.setStyleSheet("font-size:12px; color:#eaeaea; margin-bottom:6px;")
        card_layout.addWidget(participants)

        # Messages area: scrollable list of message widgets (dark panel, not white)
        self.messages_area = QtWidgets.QScrollArea()
        self.messages_area.setWidgetResizable(True)
        self.messages_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.messages_area.setStyleSheet("background: transparent; border: none;")
        self.messages_area.viewport().setStyleSheet("background: transparent;")

        self.messages_container = QtWidgets.QWidget()
        # Make inner panel dark to match theme instead of white
        self.messages_container.setStyleSheet("background: #0f1a2e; border-radius:8px;")

        self.messages_layout = QtWidgets.QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()
        self.messages_area.setWidget(self.messages_container)
        card_layout.addWidget(self.messages_area, 1)

        # Hint for dead users
        self.chat_hint_label = QtWidgets.QLabel("You are dead. Cannot send message.")
        self.chat_hint_label.setAlignment(QtCore.Qt.AlignCenter)
        self.chat_hint_label.setVisible(False)
        self.chat_hint_label.setStyleSheet(
            "font-size:12px; color:#f39c12; background-color: rgba(243,156,18,0.12); padding:6px; border-radius:6px;"
        )
        card_layout.addWidget(self.chat_hint_label)

        # Input row (styled like lobby)
        input_layout = QtWidgets.QHBoxLayout()
        self.input_box = QtWidgets.QLineEdit()
        self.input_box.setPlaceholderText("Type a message...")
        self.input_box.setStyleSheet("background:#0f1a2e; border:1px solid #0f3460; color:#eaeaea; padding:8px; border-radius:8px;")
        input_layout.addWidget(self.input_box)

        self.send_btn = QtWidgets.QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: black;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 15px;
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
        self.input_box.textChanged.connect(lambda t: self.send_btn.setEnabled(bool(t.strip()) and self.can_send_chat))

        card_layout.addLayout(input_layout)

        main_layout.addWidget(card)

        # Apply chat permissions after UI is built
        self.refresh_chat_permissions()

    def _is_me_alive(self) -> bool:
        if not self.window_manager or not self.my_username:
            return True
        players = self.window_manager.get_shared_data("room_players", [])
        if not isinstance(players, list):
            return True
        for p in players:
            if isinstance(p, dict) and p.get("username") == self.my_username:
                raw = p.get("is_alive", 1)
                try:
                    return int(raw) != 0
                except Exception:
                    return bool(raw)
        return True

    def refresh_chat_permissions(self):
        alive = self._is_me_alive()
        self.can_send_chat = bool(alive)
        if hasattr(self, "chat_hint_label"):
            self.chat_hint_label.setVisible(not self.can_send_chat)
        if hasattr(self, "input_box"):
            self.input_box.setEnabled(self.can_send_chat)
        if hasattr(self, "send_btn"):
            if not self.can_send_chat:
                self.send_btn.setEnabled(False)
            else:
                self.send_btn.setEnabled(bool(self.input_box.text().strip()))

    def on_logout(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        try:
            nc = self.network_client
            if nc:
                try:
                    nc.send_packet(208, {})
                except Exception:
                    pass
                try:
                    nc.send_packet(105, {})
                except Exception:
                    pass
            if self.window_manager:
                self.window_manager.set_shared_data("user_id", None)
                self.window_manager.set_shared_data("username", None)
                self.window_manager.set_shared_data("current_room_id", None)
                self.window_manager.set_shared_data("current_room_name", None)
                self.window_manager.set_shared_data("is_host", False)
                self.window_manager.set_shared_data("connected", False)
                self.window_manager.navigate_to("welcome")
        except Exception as e:
            if self.toast_manager:
                self.toast_manager.error(f"Logout error: {str(e)}")

    def start_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self):
        # Tính remaining từ deadline để đồng bộ với server

        self.remaining = max(0, int(self.deadline - time.time()))
        if self.remaining >= 0:
            self.timer_label.setText(f"⏱️ {self.remaining}s")
        if self.remaining <= 0:
            self.timer.stop()
            self.close()

    def sync_remaining(self, seconds: int):
        """Sync countdown with the wolf phase remaining time."""
        try:
            # Nếu có deadline, tính từ deadline; nếu không, dùng seconds
            if hasattr(self, "deadline") and self.deadline:
                self.remaining = max(0, int(self.deadline - time.time()))
            else:
                self.remaining = max(0, int(seconds))
            if hasattr(self, "timer_label"):
                self.timer_label.setText(f"⏱️ {self.remaining}s")
        except Exception:
            pass

    def handle_chat_broadcast(self, payload: dict):
        """Called by RoomWindow when receiving CHAT_BROADCAST (402)."""
        if not isinstance(payload, dict):
            return
        chat_type = payload.get("chat_type", "day")
        if chat_type != "wolf":
            return
        username = payload.get("username", "Unknown")
        message = payload.get("message", "")
        if username in self.wolf_usernames or username == self.my_username:
            self.append_message(username, message)
            print(f"[DEBUG] Wolf chat received: {username}: {message}")

    def send_message(self):
        if not self.can_send_chat:
            if self.toast_manager:
                self.toast_manager.warning("You are dead. Cannot send message!")
            return
        msg = self.input_box.text().strip()
        if msg:
            try:
                if self.send_callback:
                    self.send_callback(msg)
                # Don't append here - wait for server CHAT_BROADCAST to avoid duplicates
                self.input_box.clear()
            except Exception as e:
                print(f"[ERROR] Wolf chat send_message failed: {e}")
                import traceback
                traceback.print_exc()

    def append_message(self, username, msg):
        # Add a message widget into the messages container (left for others, right for self)
        def _esc(text):
            return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

        safe_user = _esc(username if username is not None else "")
        safe_msg = _esc(msg if msg is not None else "")

        is_self = (username == self.my_username)

        # Use 'me' label for self messages
        display_user = 'me' if is_self else safe_user

        # Message frame
        msg_frame = QtWidgets.QFrame()
        msg_frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        v = QtWidgets.QVBoxLayout(msg_frame)
        v.setContentsMargins(6, 2, 6, 2)
        v.setSpacing(4)

        user_lbl = QtWidgets.QLabel(display_user)
        user_lbl.setStyleSheet("font-size:11px; color:rgba(255,255,255,0.75);")
        v.addWidget(user_lbl, alignment=QtCore.Qt.AlignLeft if not is_self else QtCore.Qt.AlignRight)

        bubble = QtWidgets.QLabel(safe_msg)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        bubble.setContentsMargins(10, 8, 10, 8)
        bubble.setMaximumWidth(360)
        if is_self:
            bubble.setStyleSheet("background:#2ecc71; color:#062b1a; padding:8px; border-radius:12px;")
        else:
            bubble.setStyleSheet("background:#e94560; color:white; padding:8px; border-radius:12px;")
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

        # Insert just before the stretch spacer so messages stack top->down
        self.messages_layout.insertLayout(self.messages_layout.count()-1, row)

        # Auto-scroll to bottom
        QtCore.QTimer.singleShot(50, lambda: self.messages_area.verticalScrollBar().setValue(self.messages_area.verticalScrollBar().maximum()))

    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()
