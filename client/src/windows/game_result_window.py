from PyQt5 import QtWidgets, QtCore, QtGui
from components.user_header import UserHeader
from utils.image_utils import set_window_icon

class GameResultWindow(QtWidgets.QWidget):
    """Game result window - shows winner team and all player roles"""

    # Role colors
    ROLE_COLORS = {
        "werewolf": "#e74c3c",  # Red
        "seer": "#3498db",      # Blue
        "guard": "#2ecc71",     # Green
        "villager": "#95a5a6",  # Gray
    }

    ROLE_ICONS = {
        "werewolf": "🐺",
        "seer": "🔮",
        "guard": "🛡️",
        "villager": "👤",
    }

    def __init__(self, toast_manager=None, window_manager=None):
        super().__init__()
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.winner_team = None  # "villagers" or "werewolves"
        self.players_with_roles = []  # List of {username, role, is_alive}
        
        self.setObjectName("game_result_window")
        self.setWindowTitle("Werewolf - Game Over")
        self.setup_ui()

    def set_game_result(self, winner_team: str, players_with_roles: list):
        """
        Set game result data
        winner_team: "villagers" or "werewolves"
        players_with_roles: list of {username, role, is_alive}
        """
        self.winner_team = winner_team
        self.players_with_roles = players_with_roles
        self.update_display()

    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)
        
        # Get username
        my_username = self.window_manager.get_shared_data("username") if self.window_manager else None
        if my_username and hasattr(self, 'user_header'):
            self.user_header.set_username(my_username)

    def setup_ui(self):
        """Setup user interface"""
        self.resize(900, 750)
        set_window_icon(self)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main card container
        card = QtWidgets.QFrame()
        card.setObjectName("game_result_card")
        card.setStyleSheet("""
            QFrame#game_result_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 3px solid #9b59b6;
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

        # Winner announcement
        self.winner_container = QtWidgets.QWidget()
        winner_layout = QtWidgets.QVBoxLayout(self.winner_container)
        winner_layout.setSpacing(10)
        winner_layout.setContentsMargins(20, 20, 20, 20)
        
        self.winner_icon = QtWidgets.QLabel("🏆")
        self.winner_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.winner_icon.setStyleSheet("font-size: 60px;")
        winner_layout.addWidget(self.winner_icon)
        
        self.winner_title = QtWidgets.QLabel("GAME OVER")
        self.winner_title.setAlignment(QtCore.Qt.AlignCenter)
        self.winner_title.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #ffffff;
            letter-spacing: 3px;
        """)
        winner_layout.addWidget(self.winner_title)
        
        self.winner_label = QtWidgets.QLabel()
        self.winner_label.setAlignment(QtCore.Qt.AlignCenter)
        self.winner_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            padding: 10px;
            border-radius: 10px;
        """)
        winner_layout.addWidget(self.winner_label)
        
        self.card_layout.addWidget(self.winner_container)

        # Players reveal section
        reveal_title = QtWidgets.QLabel("📜 Player Roles Revealed")
        reveal_title.setAlignment(QtCore.Qt.AlignCenter)
        reveal_title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ecf0f1;
            margin-top: 10px;
        """)
        self.card_layout.addWidget(reveal_title)

        # Scrollable player cards
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)
        
        self.players_grid_widget = QtWidgets.QWidget()
        self.players_grid_layout = QtWidgets.QGridLayout(self.players_grid_widget)
        self.players_grid_layout.setSpacing(20)
        self.players_grid_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll_area.setWidget(self.players_grid_widget)
        self.card_layout.addWidget(scroll_area, 1)

        # Bottom buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(15)
        
        self.back_to_lobby_btn = QtWidgets.QPushButton("🏠 Back to Lobby")
        self.back_to_lobby_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 15px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #5dade2;
            }
            QPushButton:pressed {
                background-color: #2874a6;
            }
        """)
        self.back_to_lobby_btn.clicked.connect(self.on_back_to_lobby)
        btn_row.addWidget(self.back_to_lobby_btn)
        
        self.play_again_btn = QtWidgets.QPushButton("🔄 Play Again")
        self.play_again_btn.setStyleSheet("""
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
        """)
        self.play_again_btn.clicked.connect(self.on_play_again)
        btn_row.addWidget(self.play_again_btn)
        
        self.card_layout.addLayout(btn_row)
        
        main_layout.addWidget(card)

    def update_display(self):
        """Update display with game result data"""
        # Update winner label
        if self.winner_team == "villagers":
            self.winner_label.setText("🎉 VILLAGERS WIN! 🎉")
            self.winner_label.setStyleSheet("""
                font-size: 24px;
                font-weight: bold;
                padding: 10px;
                border-radius: 10px;
                background-color: rgba(46, 204, 113, 0.3);
                color: #2ecc71;
            """)
        elif self.winner_team == "werewolves":
            self.winner_label.setText("🐺 WEREWOLVES WIN! 🐺")
            self.winner_label.setStyleSheet("""
                font-size: 24px;
                font-weight: bold;
                padding: 10px;
                border-radius: 10px;
                background-color: rgba(231, 76, 60, 0.3);
                color: #e74c3c;
            """)
        else:
            self.winner_label.setText("Game Over")
            self.winner_label.setStyleSheet("""
                font-size: 24px;
                font-weight: bold;
                padding: 10px;
                border-radius: 10px;
                background-color: rgba(149, 165, 166, 0.3);
                color: #95a5a6;
            """)

        # Clear existing player cards
        while self.players_grid_layout.count():
            item = self.players_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create player cards
        col_count = 4
        row = 0
        col = 0
        
        for player_info in self.players_with_roles:
            if not isinstance(player_info, dict):
                continue
            
            username = player_info.get("username", "Unknown")
            role = player_info.get("role", "villager").lower()
            is_alive = bool(player_info.get("is_alive", 1))
            
            card_item = self._create_player_card(username, role, is_alive)
            self.players_grid_layout.addWidget(card_item, row, col)
            
            col += 1
            if col >= col_count:
                col = 0
                row += 1

    def _create_player_card(self, username: str, role: str, is_alive: bool):
        """Create a player card showing username and role"""
        card = QtWidgets.QFrame()
        card.setObjectName("player_reveal_card")
        
        # Get role color
        role_color = self.ROLE_COLORS.get(role, "#95a5a6")
        role_icon = self.ROLE_ICONS.get(role, "👤")
        
        card.setStyleSheet(f"""
            QFrame#player_reveal_card {{
                background-color: #1a1a2e;
                border: 3px solid {role_color};
                border-radius: 12px;
                padding: 10px;
            }}
        """)
        
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(10, 10, 10, 10)
        
        # Player icon
        icon_label = QtWidgets.QLabel(role_icon)
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        card_layout.addWidget(icon_label)
        
        # Username
        username_label = QtWidgets.QLabel(username)
        username_label.setAlignment(QtCore.Qt.AlignCenter)
        username_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #ecf0f1;
        """)
        username_label.setWordWrap(True)
        card_layout.addWidget(username_label)
        
        # Role
        role_label = QtWidgets.QLabel(role.title())
        role_label.setAlignment(QtCore.Qt.AlignCenter)
        role_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {role_color};
            background-color: rgba(255, 255, 255, 0.1);
            padding: 4px 8px;
            border-radius: 5px;
        """)
        card_layout.addWidget(role_label)
        
        # Status
        status_text = "✓ Survived" if is_alive else "✗ Dead"
        status_color = "#2ecc71" if is_alive else "#e74c3c"
        status_label = QtWidgets.QLabel(status_text)
        status_label.setAlignment(QtCore.Qt.AlignCenter)
        status_label.setStyleSheet(f"""
            font-size: 11px;
            color: {status_color};
            font-weight: bold;
        """)
        card_layout.addWidget(status_label)
        
        return card

    def on_back_to_lobby(self):
        """Leave room and navigate back to lobby"""
        if self.window_manager:
            # Leave room first
            network_client = self.window_manager.get_shared_data("network_client")
            if network_client:
                try:
                    network_client.send_packet(208, {})  # LEAVE_ROOM_REQ
                except Exception as e:
                    print(f"[WARNING] Failed to send leave room request: {e}")
            
            # Clear room data
            self.window_manager.set_shared_data("current_room_id", None)
            self.window_manager.set_shared_data("current_room_name", None)
            self.window_manager.set_shared_data("is_host", False)
            self.window_manager.set_shared_data("role_info", {})
            
            # Navigate to lobby
            self.window_manager.navigate_to("lobby")
    
    def on_play_again(self):
        """Return to the same room to play again"""
        if self.window_manager:
            # Keep room data and navigate back to room
            # The room should still exist on server (not deleted unless all players left)
            room_id = self.window_manager.get_shared_data("current_room_id")
            if room_id:
                # Navigate back to room window
                self.window_manager.navigate_to("room")
            else:
                # Room was deleted, go to lobby
                if self.toast_manager:
                    self.toast_manager.warning("Room no longer exists. Going to lobby.")
                self.window_manager.navigate_to("lobby")

    def on_logout(self):
        """Handle logout"""
        if self.toast_manager:
            self.toast_manager.info("Logging out...")
        if self.window_manager:
            self.window_manager.navigate_to("welcome")
    
    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ - cleanup network client"""
        # Check if closing by navigation or by user clicking X
        is_navigation = getattr(self, '_closing_by_navigation', False)
        
        if not is_navigation:
            # User clicked X button - cleanup and quit
            print("[DEBUG] Game result window closing by user, cleaning up...")
            try:
                network_client = self.window_manager.get_shared_data("network_client") if self.window_manager else None
                if network_client:
                    network_client.disconnect()
            except Exception as e:
                print(f"[ERROR] Error during game result cleanup: {e}")
            
            event.accept()
            # Quit application
            QtWidgets.QApplication.instance().quit()
        else:
            # Closing by navigation - just accept
            event.accept()
