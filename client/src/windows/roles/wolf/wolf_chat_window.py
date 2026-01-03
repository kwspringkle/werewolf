from PyQt5 import QtWidgets, QtCore

class WolfChatWindow(QtWidgets.QWidget):
    """Styled wolf chat (card-like, timer)"""
    def __init__(self, my_username, wolf_usernames, send_callback=None, duration_seconds=30, network_client=None, room_id=None, parent=None):
        super().__init__(parent)
        self.setObjectName("wolf_chat_window")
        self.setWindowTitle("Wolf Chat")
        self.setFixedSize(500, 600)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.send_callback = send_callback
        self.my_username = my_username
        self.wolf_usernames = wolf_usernames
        self.duration = duration_seconds
        self.remaining = duration_seconds
        self.network_client = network_client
        self.room_id = room_id
        self.setup_ui()
        self.start_timer()
        self.start_receive_timer()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

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
                background-color: #555555;
                color: #888888;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #666666;
                color: #999999;
            }
            QPushButton:pressed {
                background-color: #444444;
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
        self.input_box.textChanged.connect(lambda t: self.send_btn.setEnabled(bool(t.strip())))

        card_layout.addLayout(input_layout)

        main_layout.addWidget(card)

    def start_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self):
        self.remaining -= 1
        if self.remaining >= 0:
            self.timer_label.setText(f"⏱️ {self.remaining}s")
        if self.remaining <= 0:
            self.timer.stop()
            self.close()

    def send_message(self):
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

    def start_receive_timer(self):
        """Start timer to receive chat messages from server"""
        if self.network_client:
            self.recv_timer = QtCore.QTimer(self)
            self.recv_timer.timeout.connect(self.receive_packets)
            self.recv_timer.start(100)  # Check every 100ms

    def receive_packets(self):
        """Receive and handle packets from server"""
        if not self.network_client:
            return

        # Process ALL available packets in buffer (not just one)
        max_packets_per_tick = 10  # Prevent infinite loop
        packets_processed = 0

        while packets_processed < max_packets_per_tick:
            try:
                header, payload = self.network_client.receive_packet()
                if header is None:
                    break  # No more packets available

                packets_processed += 1

                # Handle CHAT_BROADCAST
                if header == 402:  # CHAT_BROADCAST
                    chat_type = payload.get("chat_type", "day")
                    # Only show wolf chat messages, ignore day chat
                    if chat_type == "wolf":
                        username = payload.get("username", "Unknown")
                        message = payload.get("message", "")
                        # Only show wolf messages (from wolves in this room)
                        if username in self.wolf_usernames or username == self.my_username:
                            self.append_message(username, message)
                            print(f"[DEBUG] Wolf chat received: {username}: {message}")

                # Handle PING
                elif header == 501:
                    try:
                        self.network_client.send_packet(502, {"type": "pong"})
                    except:
                        pass

            except RuntimeError as e:
                # Ignore errors during chat (server might disconnect during phase transition)
                break
            except Exception as e:
                print(f"[ERROR] Wolf chat receive error: {e}")
                break

    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'recv_timer'):
            self.recv_timer.stop()
        event.accept()
