from PyQt5 import QtWidgets, QtCore
from components.user_header import UserHeader

class SeerSelectWindow(QtWidgets.QWidget):
    """màn chọn cho role tiên tri"""
    def __init__(self, players, my_username, duration_seconds=30, network_client=None, room_id=None, parent=None, window_manager=None, toast_manager=None):
        super().__init__(parent)
        # Normal window (movable, consistent sizing via WindowManager)
        self.use_default_size = True
        self.preserve_window_flags = False
        self.players = players
        self.my_username = my_username
        self.duration = duration_seconds
        self.remaining = duration_seconds
        self.network_client = network_client
        self.room_id = room_id
        self.window_manager = window_manager
        self.toast_manager = toast_manager
        self.selected_username = None
        self.my_is_alive = True
        try:
            for p in (players or []):
                if isinstance(p, dict) and p.get("username") == my_username:
                    self.my_is_alive = int(p.get("is_alive", 1)) != 0
                    break
        except Exception:
            self.my_is_alive = True
        self.setObjectName("seer_select_window")
        self.setWindowTitle("Seer — Pick a player")
        self.setup_ui()
        self.start_timer()
    
    def showEvent(self, event):
        """Called when window is shown - update username from shared_data"""
        super().showEvent(event)
        # Update username from shared_data to ensure it's current
        if self.window_manager:
            username = self.window_manager.get_shared_data("username")
            if username and hasattr(self, 'user_header'):
                self.user_header.set_username(username)
                self.my_username = username

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # User header
        self.user_header = UserHeader(self)
        self.user_header.set_username(self.my_username or "Player")
        self.user_header.logout_clicked.connect(self.on_logout)
        main_layout.addWidget(self.user_header)

        card = QtWidgets.QFrame()
        card.setObjectName("seer_card")
        card.setStyleSheet("""
            QFrame#seer_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 3px solid #f39c12;
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
            color: #f39c12;
            font-weight: bold;
            background-color: rgba(243, 156, 18, 0.1);
            padding: 8px;
            border-radius: 5px;
        """)
        self.card_layout.addWidget(self.timer_label)

        icon_label = QtWidgets.QLabel("🔮")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 100px;")
        self.card_layout.addWidget(icon_label)

        title_label = QtWidgets.QLabel("Seer: Choose a player to reveal")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; color: #f39c12; font-weight: bold;")
        self.card_layout.addWidget(title_label)

        hint_label = QtWidgets.QLabel("Hint: You already know your own role.")
        hint_label.setAlignment(QtCore.Qt.AlignCenter)
        hint_label.setStyleSheet("font-size: 12px; color: #cccccc; margin-top: 2px;")
        self.card_layout.addWidget(hint_label)

        self.dead_hint_label = QtWidgets.QLabel("You are dead. Cannot select anyone. You can still press Skip.")
        self.dead_hint_label.setAlignment(QtCore.Qt.AlignCenter)
        self.dead_hint_label.setVisible(not self.my_is_alive)
        self.dead_hint_label.setStyleSheet("""
            font-size: 12px;
            color: #f39c12;
            background-color: rgba(243, 156, 18, 0.12);
            padding: 6px;
            border-radius: 6px;
            margin-top: 6px;
        """)
        self.card_layout.addWidget(self.dead_hint_label)


        # Grid chọn user dạng card nhỏ vuông như lobby
        self.user_grid_widget = QtWidgets.QWidget()
        self.user_grid_layout = QtWidgets.QGridLayout(self.user_grid_widget)
        self.user_grid_layout.setSpacing(15)
        self.user_grid_layout.setContentsMargins(10, 10, 10, 10)

        self.user_cards = []
        col_count = 3
        row = 0
        col = 0
        safe_players = []
        for p in (self.players or []):
            if isinstance(p, dict) or isinstance(p, str):
                safe_players.append(p)

        print(f"[DEBUG] SeerSelectWindow rendering {len(safe_players)} players")
        for p in safe_players:
            uname = (p.get("username") if isinstance(p, dict) else str(p))
            if not uname:
                uname = "(Unknown)"
            raw_alive = p.get("is_alive", 1) if isinstance(p, dict) else 1
            try:
                is_alive = int(raw_alive) != 0
            except Exception:
                is_alive = bool(raw_alive)

            is_self = (uname == self.my_username)

            card_item = QtWidgets.QFrame()
            card_item.setObjectName("user_card")
            card_item.setFrameShape(QtWidgets.QFrame.StyledPanel)
            
            # Style khác nhau cho alive và dead players
            if is_alive:
                card_item.setStyleSheet("""
                    QFrame#user_card {
                        background-color: #1a1a2e;
                        border: 2px solid #f39c12;
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

            # Disable self (seer already knows own role)
            if is_self:
                card_item.setCursor(QtCore.Qt.ForbiddenCursor)
                card_item.setEnabled(False)
                name_label.setText(uname + "\n(You — already know)")

            # If seer is dead: show cards but disable selection (only allow skip)
            # If seer is alive: allow selection of alive players (not self)
            if self.my_is_alive and is_alive and (not is_self):
                card_item.mousePressEvent = self._make_card_click(card_item, uname)
                card_item.setCursor(QtCore.Qt.PointingHandCursor)
            else:
                # Dead seer or dead target or self: không thể click, cursor mặc định
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
        
        self.select_btn = QtWidgets.QPushButton("Reveal")
        self.select_btn.setMinimumHeight(35)
        self.select_btn.setEnabled(False)  # Disabled until player is selected
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #e94560;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #ff5770;
            }
            QPushButton:pressed {
                background-color: #d03550;
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

    def _make_card_click(self, card_item, uname):
        def handler(event):
            # Tìm player trong user_cards
            player_info = next((c, u, a) for c, u, a in self.user_cards if u == uname)
            if not player_info:
                return
            
            _, _, is_alive = player_info
            # Only allow selection if player is alive
            if not is_alive:
                return
            
            # Bỏ chọn tất cả
            for c, _, alive in self.user_cards:
                if alive:  # Only update style for alive players
                    c.setProperty("selected", False)
                    # Update style to show unselected
                    c.setStyleSheet("""
                        QFrame#user_card {
                            background-color: #1a1a2e;
                            border: 2px solid #f39c12;
                            border-radius: 10px;
                        }
                    """)
            
            # Chọn card này
            card_item.setProperty("selected", True)
            card_item.setStyleSheet("""
                QFrame#user_card {
                    background-color: #2a3a4e;
                    border: 3px solid #f39c12;
                    border-radius: 10px;
                }
            """)
            self.selected_username = uname
            # Enable select button
            self.select_btn.setEnabled(True)
        return handler

    def on_select(self):
        if not self.my_is_alive:
            try:
                QtWidgets.QMessageBox.information(self, "Info", "You are dead. Cannot select anyone.")
            except Exception:
                pass
            return
        target = self.selected_username
        if not target:
            QtWidgets.QMessageBox.warning(self, "Select player", "Please select a player to reveal")
            return
        
        # Disable buttons to prevent multiple clicks
        self.select_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        
        # Stop timer
        if hasattr(self, 'timer'):
            self.timer.stop()
        
        if self.network_client and self.room_id is not None:
            try:
                print(f"[DEBUG] Sending SEER_CHECK_REQ for target: {target}")
                # Prefer wrapper method if available
                if hasattr(self.network_client, "send_seer_check"):
                    self.network_client.send_seer_check(self.room_id, target)
                else:
                    self.network_client.send_packet(405, {
                        "room_id": self.room_id,
                        "target_username": target
                    })
            except Exception as e:
                print(f"[ERROR] Error sending seer request: {e}")
                QtWidgets.QMessageBox.warning(self, "Network", "Failed to send seer request")
                # Re-enable on failure
                self.select_btn.setEnabled(True)
                self.skip_btn.setEnabled(True)
                if hasattr(self, 'timer'):
                    self.timer.start(1000)
                return

        # Close window - wait for SEER_RESULT broadcast
        self.close()

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
            # Best-effort: tell server
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
                # Re-enable buttons on error
                self.select_btn.setEnabled(True)
                self.skip_btn.setEnabled(True)
                if hasattr(self, 'timer'):
                    self.timer.start(1000)
        
        # Don't close immediately - wait for SEER_RESULT (406) from server
        # The window will be closed when result is received

    def on_skip(self):
        # Stop timer
        if hasattr(self, 'timer'):
            self.timer.stop()
        # Disable buttons
        self.select_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        # Send skip to server so phase can advance immediately
        if self.network_client and self.room_id is not None:
            try:
                if hasattr(self.network_client, "send_seer_check"):
                    self.network_client.send_seer_check(self.room_id, "")
                else:
                    self.network_client.send_packet(405, {"room_id": self.room_id, "target_username": ""})
            except Exception:
                pass
        # Close window - will trigger destroyed signal
        self.close()

    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()