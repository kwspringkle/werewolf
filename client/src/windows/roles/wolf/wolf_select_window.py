from PyQt5 import QtWidgets, QtCore
from components.user_header import UserHeader

class WolfSelectWindow(QtWidgets.QWidget):
    """Wolf selection window: choose a living target to bite (UI-only selection until submit)."""

    _CARD_STYLE_ALIVE = """
        QFrame#user_card {
            background-color: #1a1a2e;
            border: 2px solid #e94560;
            border-radius: 10px;
        }
    """
    _CARD_STYLE_ALIVE_SELECTED = """
        QFrame#user_card {
            background-color: #3a1a2e;
            border: 3px solid #e94560;
            border-radius: 10px;
        }
    """
    _CARD_STYLE_DEAD = """
        QFrame#user_card {
            background-color: #333333;
            border: 2px solid #555555;
            border-radius: 10px;
            opacity: 0.6;
        }
    """

    def __init__(
        self,
        player_list,
        alive_status,
        my_username=None,
        duration_seconds=60,
        network_client=None,
        room_id=None,
        can_vote: bool = True,
        parent=None,
        window_manager=None,
        toast_manager=None,
    ):
        super().__init__(parent)
        self.use_default_size = True
        self.preserve_window_flags = False
        self.player_list = player_list
        self.alive_status = alive_status
        self.my_username = my_username
        self.duration = duration_seconds
        self.remaining = duration_seconds
        self.network_client = network_client
        self.room_id = room_id
        self.window_manager = window_manager
        self.toast_manager = toast_manager
        self.selected_username = None
        self.can_vote = bool(can_vote)

        self.setObjectName("wolf_select_window")
        self.setWindowTitle("Wolf — Choose a victim")
        self.setup_ui()
        self.start_timer()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.user_header = UserHeader(self)
        self.user_header.set_username(self.my_username or "Player")
        self.user_header.logout_clicked.connect(self.on_logout)
        main_layout.addWidget(self.user_header)

        card = QtWidgets.QFrame()
        card.setObjectName("wolf_card")
        card.setStyleSheet("""
            QFrame#wolf_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 3px solid #e94560;
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

        # Header
        header_v = QtWidgets.QVBoxLayout()

        title_label = QtWidgets.QLabel("Wolves: Choose a player to bite")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; color: #e94560; font-weight: bold; margin-top: 4px;")
        header_v.addWidget(title_label, alignment=QtCore.Qt.AlignCenter)

        self.dead_hint_label = QtWidgets.QLabel("You are dead. You cannot vote.")
        self.dead_hint_label.setAlignment(QtCore.Qt.AlignCenter)
        self.dead_hint_label.setVisible(not self.can_vote)
        self.dead_hint_label.setStyleSheet("""
            font-size: 12px;
            color: #f39c12;
            background-color: rgba(243, 156, 18, 0.12);
            padding: 6px;
            border-radius: 6px;
            margin-top: 6px;
        """)
        header_v.addWidget(self.dead_hint_label)

        self.card_layout.addLayout(header_v)

        # Grid of players (cards)
        self.user_grid_widget = QtWidgets.QWidget()
        self.user_grid_layout = QtWidgets.QGridLayout(self.user_grid_widget)
        self.user_grid_layout.setSpacing(15)
        self.user_grid_layout.setContentsMargins(10, 10, 10, 10)

        self.user_cards = []
        col_count = 3
        row = 0
        col = 0
        for i, uname in enumerate(self.player_list):
            raw_alive = self.alive_status[i] if i < len(self.alive_status) else 1
            try:
                is_alive = int(raw_alive) != 0
            except Exception:
                is_alive = bool(raw_alive)

            card_item = QtWidgets.QFrame()
            card_item.setObjectName("user_card")
            card_item.setFrameShape(QtWidgets.QFrame.StyledPanel)
            
            if is_alive:
                card_item.setStyleSheet(self._CARD_STYLE_ALIVE)
            else:
                card_item.setStyleSheet(self._CARD_STYLE_DEAD)

            card_item_layout = QtWidgets.QVBoxLayout(card_item)
            card_item_layout.setSpacing(0)
            card_item_layout.setContentsMargins(5, 5, 5, 5)

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

            if is_alive and self.can_vote:
                card_item.mousePressEvent = self._make_card_click(card_item, uname)
                card_item.setCursor(QtCore.Qt.PointingHandCursor)
            else:
                card_item.setCursor(QtCore.Qt.ForbiddenCursor)
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

        self.select_btn = QtWidgets.QPushButton("Bite")
        self.select_btn.setMinimumHeight(35)
        self.select_btn.setEnabled(False)  # Disabled until a living player is selected
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

        # Chat button
        self.chat_btn = QtWidgets.QPushButton("💬  Chat with other wolves")
        self.chat_btn.setMinimumHeight(36)
        self.chat_btn.setMinimumWidth(180)
        self.chat_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #1a1a2e;
                border: 2px solid rgba(233,69,96,0.12);
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                border-color: #e94560;
                box-shadow: 0px 4px 10px rgba(233,69,96,0.1);
            }
            QPushButton:pressed {
                background-color: #f8f8f8;
            }
            QPushButton:disabled {
                background-color: #efefef;
                color: #999999;
                border-color: rgba(0,0,0,0.06);
            }
        """)
        self.card_layout.addWidget(self.chat_btn, alignment=QtCore.Qt.AlignCenter)

        self.card_layout.addStretch()
        main_layout.addWidget(card)

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
        self.remaining -= 1
        if self.remaining >= 0:
            self.timer_label.setText(f"⏱️ {self.remaining}s")
        if self.remaining <= 0:
            self.timer.stop()
            self.on_skip()

    def _make_card_click(self, card_item, uname):
        def handler(event):
            # Before submit, wolves can change target freely by clicking another card.
            for c, _, alive in self.user_cards:
                if alive:
                    c.setProperty("selected", False)
                    c.setStyleSheet(self._CARD_STYLE_ALIVE)

            card_item.setProperty("selected", True)
            card_item.setStyleSheet(self._CARD_STYLE_ALIVE_SELECTED)

            self.selected_username = uname
            self.select_btn.setEnabled(True)
        return handler

    def get_selected_username(self):
        return self.selected_username

    def on_select(self):
        if not self.can_vote:
            if self.toast_manager:
                self.toast_manager.warning("You are dead. You cannot vote.")
            return
        target = self.selected_username
        if not target:
            QtWidgets.QMessageBox.warning(self, "Select player", "Please select a player to bite")
            return
        
        target_index = -1
        for i, uname in enumerate(self.player_list):
            if uname == target:
                target_index = i
                break
        
        if target_index >= 0 and not self.alive_status[target_index]:
            QtWidgets.QMessageBox.warning(self, "Invalid target", "Cannot bite a dead player")
            return
        
        # Disable buttons to prevent multiple submits
        self.select_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        
        if hasattr(self, 'timer'):
            self.timer.stop()
        
        if self.network_client and self.room_id is not None:
            try:
                self.network_client.send_wolf_kill(self.room_id, target)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Network", f"Failed to send wolf kill: {e}")
                # Re-enable buttons on error (allow changing selection and re-submit)
                self.select_btn.setEnabled(True)
                self.skip_btn.setEnabled(True)
                if hasattr(self, 'timer'):
                    self.timer.start(1000)
                return
        
        # Close window; server will send (optional) WOLF_KILL_RES ack and later PHASE_DAY
        self.close()

    def on_skip(self):
        self.close()

    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()
