from PyQt5 import QtWidgets, QtCore

class GuardSelectWindow(QtWidgets.QWidget):
    """Guard selection screen styled like RoleCardWindow, with countdown"""
    def __init__(self, players, my_username, duration_seconds=30, network_client=None, room_id=None, parent=None):
        super().__init__(parent)
        self.players = players
        self.my_username = my_username
        self.duration = duration_seconds
        self.remaining = duration_seconds
        self.network_client = network_client
        self.room_id = room_id
        self.selected_username = None
        self.setObjectName("guard_select_window")
        self.setWindowTitle("Guard — Protect a player")
        self.setFixedSize(500, 600)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.setup_ui()
        self.start_timer()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        card = QtWidgets.QFrame()
        card.setObjectName("guard_card")
        card.setStyleSheet("""
            QFrame#guard_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 3px solid #43d9ad;
                border-radius: 15px;
            }
        """)
        
        self.card_layout = QtWidgets.QVBoxLayout()
        self.card_layout.setSpacing(20)
        self.card_layout.setContentsMargins(30, 30, 30, 30)
        card.setLayout(self.card_layout)

        self.timer_label = QtWidgets.QLabel(f"⏱️ {self.remaining}s")
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        self.timer_label.setStyleSheet("""
            font-size: 18px;
            color: #43d9ad;
            font-weight: bold;
            background-color: rgba(67, 217, 173, 0.1);
            padding: 8px;
            border-radius: 5px;
        """)
        self.card_layout.addWidget(self.timer_label)

        icon_label = QtWidgets.QLabel("🛡️")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 100px;")
        self.card_layout.addWidget(icon_label)

        title_label = QtWidgets.QLabel("Guard: Choose a player to protect")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; color: #43d9ad; font-weight: bold;")
        self.card_layout.addWidget(title_label)

        # Grid chọn user dạng card nhỏ vuông như lobby
        self.user_grid_widget = QtWidgets.QWidget()
        self.user_grid_layout = QtWidgets.QGridLayout(self.user_grid_widget)
        self.user_grid_layout.setSpacing(15)
        self.user_grid_layout.setContentsMargins(10, 10, 10, 10)

        self.user_cards = []
        col_count = 3
        row = 0
        col = 0
        for p in self.players:
            uname = p.get("username") if isinstance(p, dict) else str(p)
            is_alive = p.get("is_alive", 1) if isinstance(p, dict) else 1

            card_item = QtWidgets.QFrame()
            card_item.setObjectName("user_card")
            card_item.setFrameShape(QtWidgets.QFrame.StyledPanel)
            
            # Style khác nhau cho alive và dead players
            if is_alive:
                card_item.setStyleSheet("""
                    QFrame#user_card {
                        background-color: #1a1a2e;
                        border: 2px solid #43d9ad;
                        border-radius: 10px;
                    }
                """)
            else:
                card_item.setStyleSheet("""
                    QFrame#user_card {
                        background-color: #333333;
                        border: 2px solid #555555;
                        border-radius: 10px;
                        opacity: 0.6;
                    }
                """)

            card_item_layout = QtWidgets.QVBoxLayout(card_item)
            card_item_layout.setSpacing(0)
            card_item_layout.setContentsMargins(5, 5, 5, 5)

            # Icon: 💀 cho dead, 👤 cho alive
            icon_label = QtWidgets.QLabel("💀" if not is_alive else "👤")
            icon_label.setAlignment(QtCore.Qt.AlignCenter)
            icon_label.setStyleSheet("font-size: 32px; padding-top: 5px;")
            card_item_layout.addWidget(icon_label)

            name_label = QtWidgets.QLabel(uname + ("\n(Dead)" if not is_alive else ""))
            name_label.setAlignment(QtCore.Qt.AlignCenter)
            name_label.setStyleSheet(f"""
                font-size: 11px;
                font-weight: bold;
                color: {'#888888' if not is_alive else '#eaeaea'};
                padding: 2px;
                background-color: transparent;
            """)
            name_label.setWordWrap(True)
            card_item_layout.addWidget(name_label)

            # Chỉ make clickable nếu player còn sống
            if is_alive:
                card_item.mousePressEvent = self._make_card_click(card_item, uname, is_alive)
                card_item.setCursor(QtCore.Qt.PointingHandCursor)
            else:
                # Dead player: không thể click, cursor mặc định
                card_item.setCursor(QtCore.Qt.ForbiddenCursor)
                # Disable card để không thể tương tác
                card_item.setEnabled(False)
            
            self.user_cards.append((card_item, uname, is_alive))
            self.user_grid_layout.addWidget(card_item, row, col)
            col += 1
            if col >= col_count:
                col = 0
                row += 1
        self.card_layout.addWidget(self.user_grid_widget)
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(10)
        self.skip_btn = QtWidgets.QPushButton("Skip")
        self.skip_btn.setMinimumHeight(35)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: #888888;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #666666;
                color: #999999;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
        """)
        self.skip_btn.clicked.connect(self.on_skip)
        btn_layout.addWidget(self.skip_btn)
        self.select_btn = QtWidgets.QPushButton("Protect")
        self.select_btn.setMinimumHeight(35)
        self.select_btn.setEnabled(False)  # Disabled until player is selected
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #43d9ad;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #5fffd0;
            }
            QPushButton:pressed {
                background-color: #2bbd7e;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.select_btn.clicked.connect(self.on_select)
        btn_layout.addWidget(self.select_btn)
        self.card_layout.addLayout(btn_layout)
        self.card_layout.addStretch()
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
            self.on_skip()

    def _make_card_click(self, card_item, uname, is_alive):
        def handler(event):
            # Only allow selection if player is alive
            if not is_alive:
                return
            
            # Guard có thể chọn chính mình (bảo vệ chính mình)
            # Bỏ chọn tất cả
            for c, _, alive in self.user_cards:
                if alive:  # Only update style for alive players
                    c.setProperty("selected", False)
                    # Update style to show unselected
                    c.setStyleSheet("""
                        QFrame#user_card {
                            background-color: #1a1a2e;
                            border: 2px solid #43d9ad;
                            border-radius: 10px;
                        }
                    """)
            
            # Chọn card này
            card_item.setProperty("selected", True)
            card_item.setStyleSheet("""
                QFrame#user_card {
                    background-color: #2a4a5e;
                    border: 3px solid #43d9ad;
                    border-radius: 10px;
                }
            """)
            self.selected_username = uname
            # Enable protect button
            self.select_btn.setEnabled(True)
        return handler

    def on_select(self):
        target = self.selected_username
        if not target:
            QtWidgets.QMessageBox.warning(self, "Select player", "Please select a player to protect")
            return
        
        # Disable buttons to prevent multiple clicks
        self.select_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        
        # Stop timer
        if hasattr(self, 'timer'):
            self.timer.stop()
        
        if self.network_client and self.room_id is not None:
            try:
                # Gửi GUARD_PROTECT_REQ (407) đến server
                print(f"[DEBUG] Sending GUARD_PROTECT_REQ for target: {target}")
                self.network_client.send_packet(407, {
                    "room_id": self.room_id,
                    "target_username": target
                })
            except Exception as e:
                print(f"[ERROR] Error sending guard protect request: {e}")
                QtWidgets.QMessageBox.warning(self, "Network", "Failed to send guard protect request")
                # Re-enable buttons on error
                self.select_btn.setEnabled(True)
                self.skip_btn.setEnabled(True)
                if hasattr(self, 'timer'):
                    self.timer.start(1000)
                return
        
        # Close window - server sẽ broadcast PHASE_WOLF_START khi guard chọn xong
        self.close()

    def on_skip(self):
        # Stop timer
        if hasattr(self, 'timer'):
            self.timer.stop()
        # Disable buttons
        self.select_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        # Close window - server sẽ broadcast PHASE_WOLF_START khi timeout
        # Không cần gửi gì lên server, chỉ cần đóng window
        self.close()

    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()
