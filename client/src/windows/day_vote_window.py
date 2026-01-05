from PyQt5 import QtWidgets, QtCore
from components.user_header import UserHeader
from utils.image_utils import set_window_icon

class DayVoteWindow(QtWidgets.QWidget):
    """Day phase voting window - all players vote to eliminate someone"""

    _CARD_STYLE_ALIVE = """
        QFrame#user_card {
            background-color: #1a1a2e;
            border: 2px solid #f39c12;
            border-radius: 10px;
        }
    """
    _CARD_STYLE_ALIVE_SELECTED = """
        QFrame#user_card {
            background-color: #3a2a1e;
            border: 3px solid #f39c12;
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

    def __init__(self, toast_manager=None, window_manager=None):
        super().__init__()
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.network_client = None
        self.current_room_id = None
        self.my_username = None
        self.selected_username = None
        self.has_voted = False
        self.my_is_alive = True
        self.remaining_time = 60
        self.timer = None
        
        self.setObjectName("day_vote_window")
        self.setWindowTitle("Werewolf - Day Vote")
        self.setup_ui()

    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)

        # Get shared data
        self.network_client = self.window_manager.get_shared_data("network_client")
        self.current_room_id = self.window_manager.get_shared_data("current_room_id")
        self.my_username = self.window_manager.get_shared_data("username")
        
        # Get deadline from shared data if available
        deadline = self.window_manager.get_shared_data("day_vote_deadline")
        if deadline:
            import time
            self.remaining_time = max(0, int(deadline - time.time()))
        
        print(f"[DEBUG] DayVoteWindow shown - network_client: {self.network_client is not None}, room_id: {self.current_room_id}, username: {self.my_username}")

        # Set username in header
        if self.my_username:
            self.user_header.set_username(self.my_username)
        
        # Get players and check if I'm alive
        players = self.window_manager.get_shared_data("room_players", [])
        self.my_is_alive = True
        for p in players:
            if isinstance(p, dict):
                if p.get("username") == self.my_username:
                    try:
                        self.my_is_alive = int(p.get("is_alive", 1)) != 0
                    except Exception:
                        self.my_is_alive = True
                    break
        
        # Rebuild player cards
        self.rebuild_player_cards()
        
        # Reset vote state - IMPORTANT: reset on every showEvent to allow voting in day 2, 3, etc.
        self.selected_username = None
        self.has_voted = False
        # Re-enable buttons if alive
        if self.my_is_alive:
            self.submit_btn.setEnabled(False)  # Will be enabled when player selected
            self.skip_btn.setEnabled(True)  # Skip is always available

        # Dead voter hint + disable voting UI
        if hasattr(self, "dead_hint_label"):
            self.dead_hint_label.setVisible(not bool(self.my_is_alive))
        if not self.my_is_alive:
            self.submit_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)
        else:
            # Alive: enable skip, submit will be enabled when player selected
            self.skip_btn.setEnabled(True)
        
        # Only run local countdown if we don't have a shared server deadline
        if not deadline:
            self.start_timer()

    def hideEvent(self, event):
        """Called when window is hidden"""
        super().hideEvent(event)
        if self.timer:
            self.timer.stop()
            self.timer = None

    def setup_ui(self):
        """Setup user interface"""
        self.resize(800, 700)
        set_window_icon(self)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main card container
        card = QtWidgets.QFrame()
        card.setObjectName("day_vote_card")
        card.setStyleSheet("""
            QFrame#day_vote_card {
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
        
        # User header
        self.user_header = UserHeader(self)
        self.user_header.logout_clicked.connect(self.on_logout)
        self.card_layout.addWidget(self.user_header)

        # Timer label
        self.timer_label = QtWidgets.QLabel(f"⏱️ {self.remaining_time}s")
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

        # Hint for dead voters
        self.dead_hint_label = QtWidgets.QLabel("Bạn đã chết nên không thể vote")
        self.dead_hint_label.setAlignment(QtCore.Qt.AlignCenter)
        self.dead_hint_label.setVisible(False)
        self.dead_hint_label.setStyleSheet("""
            font-size: 12px;
            color: #f39c12;
            background-color: rgba(243, 156, 18, 0.12);
            padding: 6px;
            border-radius: 6px;
        """)
        self.card_layout.addWidget(self.dead_hint_label)

        # Header
        header_v = QtWidgets.QVBoxLayout()

        sun_label = QtWidgets.QLabel("☀️ 🗳️")
        sun_label.setAlignment(QtCore.Qt.AlignCenter)
        sun_label.setStyleSheet("font-size: 36px;")
        header_v.addWidget(sun_label)

        title_label = QtWidgets.QLabel("Day Phase: Vote to Eliminate")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; color: #f39c12; font-weight: bold; margin-top: 4px;")
        header_v.addWidget(title_label)

        subtitle = QtWidgets.QLabel("Select a player you suspect is a werewolf")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 13px; color: #cccccc; margin-top: 2px;")
        header_v.addWidget(subtitle)

        self.card_layout.addLayout(header_v)

        # Grid of players (cards)
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        
        self.user_grid_widget = QtWidgets.QWidget()
        self.user_grid_layout = QtWidgets.QGridLayout(self.user_grid_widget)
        self.user_grid_layout.setSpacing(15)
        self.user_grid_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll_area.setWidget(self.user_grid_widget)
        self.card_layout.addWidget(scroll_area, 1)

        # Button row
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(15)

        # Go to chat button
        self.chat_btn = QtWidgets.QPushButton("💬 Go to Day Chat")
        self.chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 20px;
            }
            QPushButton:hover {
                background-color: #5dade2;
            }
            QPushButton:pressed {
                background-color: #2874a6;
            }
        """)
        self.chat_btn.clicked.connect(self.on_go_to_chat)
        btn_row.addWidget(self.chat_btn)

        # Submit vote button
        self.submit_btn = QtWidgets.QPushButton("✓ Submit Vote")
        self.submit_btn.setEnabled(False)
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 15px;
                padding: 12px 24px;
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
        self.submit_btn.clicked.connect(self.on_submit_vote)
        btn_row.addWidget(self.submit_btn)

        # Skip vote button
        self.skip_btn = QtWidgets.QPushButton("⏭️ Skip Vote")
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 20px;
            }
            QPushButton:hover {
                background-color: #b8c4c5;
            }
            QPushButton:pressed {
                background-color: #7f8c8d;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.skip_btn.clicked.connect(self.on_skip_vote)
        btn_row.addWidget(self.skip_btn)

        self.card_layout.addLayout(btn_row)

        main_layout.addWidget(card)

    def rebuild_player_cards(self):
        """Rebuild player cards from shared data"""
        # Clear existing cards
        while self.user_grid_layout.count():
            item = self.user_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get players from shared data
        players = self.window_manager.get_shared_data("room_players", [])
        
        if not players:
            print("[DEBUG] No players found in shared data")
            return
        
        self.user_cards = []
        col_count = 4
        row = 0
        col = 0
        
        for player in players:
            if not isinstance(player, dict):
                continue
            
            username = player.get("username", "Unknown")
            try:
                is_alive = int(player.get("is_alive", 1)) != 0
            except Exception:
                is_alive = True
            
            is_self = (username == self.my_username)

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

            label_name = username
            if is_self:
                label_name = f"{label_name}\n(You)"
            if not is_alive:
                label_name = label_name + "\n(Dead)"

            name_label = QtWidgets.QLabel(label_name)
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

            if is_alive and self.my_is_alive and not self.has_voted:
                card_item.mousePressEvent = self._make_card_click(card_item, username)
                card_item.setCursor(QtCore.Qt.PointingHandCursor)
            else:
                card_item.setCursor(QtCore.Qt.ForbiddenCursor)
                card_item.setEnabled(False)

            self.user_cards.append((card_item, username, is_alive))
            self.user_grid_layout.addWidget(card_item, row, col)
            
            col += 1
            if col >= col_count:
                col = 0
                row += 1

    def _make_card_click(self, card_widget, username):
        """Create click handler for a card"""
        def handler(event):
            if self.has_voted:
                if self.toast_manager:
                    self.toast_manager.warning("You have already voted!")
                return
            
            if not self.my_is_alive:
                if self.toast_manager:
                    self.toast_manager.warning("Dead players cannot vote!")
                return
            
            # Deselect previous selection
            if self.selected_username:
                for card, uname, is_alive in self.user_cards:
                    if uname == self.selected_username and is_alive:
                        card.setStyleSheet(self._CARD_STYLE_ALIVE)
                        break
            
            # Select this card
            self.selected_username = username
            card_widget.setStyleSheet(self._CARD_STYLE_ALIVE_SELECTED)
            self.submit_btn.setEnabled(True)
            
            print(f"[DEBUG] Selected player for voting: {username}")
        
        return handler

    def start_timer(self):
        """Start countdown timer"""
        if self.timer:
            self.timer.stop()
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(1000)  # 1 second interval
        
    def _update_timer(self):
        """Update timer display"""
        self.remaining_time -= 1
        self.timer_label.setText(f"⏱️ {self.remaining_time}s")
        
        if self.remaining_time <= 0:
            if self.timer:
                self.timer.stop()
            self.timer_label.setText("⏱️ Time's up!")
            # Auto-submit or disable voting
            if not self.has_voted:
                self.on_skip_vote()

    def handle_vote_status_update(self, payload: dict):
        """Handle VOTE_STATUS_UPDATE (410) from server"""
        if not isinstance(payload, dict):
            return
        
        # Update vote counts display (optional)
        # For now, just log it
        print(f"[DEBUG] Vote status update: {payload}")

    def on_submit_vote(self):
        """Submit vote"""
        if not self.my_is_alive:
            if self.toast_manager:
                self.toast_manager.warning("You are dead. You cannot vote.")
            return
        if not self.selected_username:
            if self.toast_manager:
                self.toast_manager.warning("Please select a player to vote!")
            return
        
        if self.has_voted:
            if self.toast_manager:
                self.toast_manager.warning("You have already voted!")
            return
        
        if not self.network_client or not self.current_room_id:
            if self.toast_manager:
                self.toast_manager.error("Network error")
            return
        
        try:
            print(f"[DEBUG] Sending vote for: {self.selected_username}")
            self.network_client.send_day_vote(self.current_room_id, self.selected_username)
            
            self.has_voted = True
            self.submit_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)
            
            # Disable all cards
            for card, _, _ in self.user_cards:
                card.setEnabled(False)
                card.setCursor(QtCore.Qt.ForbiddenCursor)
            
            if self.toast_manager:
                self.toast_manager.success(f"Voted for {self.selected_username}!")
            
        except Exception as e:
            print(f"[ERROR] Failed to send vote: {e}")
            if self.toast_manager:
                self.toast_manager.error(f"Failed to send vote: {e}")

    def on_skip_vote(self):
        """Skip voting"""
        if self.has_voted:
            if self.toast_manager:
                self.toast_manager.warning("You have already voted!")
            return
        
        if not self.my_is_alive:
            if self.toast_manager:
                self.toast_manager.warning("Bạn đã chết nên không thể vote")
            return

        # Send empty vote to server as skip
        if self.toast_manager:
            self.toast_manager.info("You skipped voting")
        
        self.has_voted = True
        self.submit_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        
        try:
            if self.network_client and self.current_room_id:
                self.network_client.send_day_vote(self.current_room_id, "")
        except Exception as e:
            print(f"[WARNING] Failed to send skip vote: {e}")

    def on_go_to_chat(self):
        """Navigate to day chat window"""
        if self.window_manager:
            self.window_manager.navigate_to("day_chat")

    def on_logout(self):
        """Handle logout"""
        if self.toast_manager:
            self.toast_manager.info("Logging out...")
        # Handle logout logic
        if self.window_manager:
            self.window_manager.navigate_to("welcome")
    
    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        # Never disconnect the shared network client here.
        event.accept()
