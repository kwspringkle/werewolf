from PyQt5 import QtWidgets, QtCore
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.user_header import UserHeader

class DeathAnnouncementWindow(QtWidgets.QWidget):
    """Window hiển thị danh sách người chết sau đêm (10 giây)"""
    def __init__(self, toast_manager=None, window_manager=None):
        super().__init__()
        # Normal window (movable, consistent sizing via WindowManager)
        self.use_default_size = True
        self.preserve_window_flags = False
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.duration = 5
        self.remaining = 5
        self.timer = None
        self.dead_players = []  # List of usernames who died
        self.setObjectName("death_announcement_window")
        self.setWindowTitle("Night Results")
        self.setup_ui()
        
    def set_dead_players(self, dead_players):
        """Set danh sách người chết và cập nhật UI"""
        self.dead_players = dead_players
        self.update_death_list()
        
    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)
        # Set username cho user_header
        username = self.window_manager.get_shared_data("username", "Player")
        self.user_header.set_username(username)
        self.remaining = self.duration
        self.timer_label.setText(f"⏱️ {self.remaining}s")
        self.start_timer()
        
    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # User header (username + logout)
        self.user_header = UserHeader(self)
        self.user_header.logout_clicked.connect(self.on_logout)
        main_layout.addWidget(self.user_header)

        card = QtWidgets.QFrame()
        card.setObjectName("death_announcement_card")
        card.setStyleSheet("""
            QFrame#death_announcement_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 3px solid #e74c3c;
                border-radius: 15px;
            }
        """)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(20)
        card_layout.setContentsMargins(40, 40, 40, 40)

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
        card_layout.addWidget(self.timer_label)

        # Icon
        icon_label = QtWidgets.QLabel("💀")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 100px;")
        card_layout.addWidget(icon_label)

        # Title
        title_label = QtWidgets.QLabel("NIGHT RESULTS")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 36px;
            color: #e74c3c;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        card_layout.addWidget(title_label)

        # Subtitle
        subtitle = QtWidgets.QLabel("Last night's victims:")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 18px; color: #cccccc; margin-top: 10px;")
        card_layout.addWidget(subtitle)

        # Death list container
        self.death_list_container = QtWidgets.QWidget()
        self.death_list_container.setStyleSheet("background: rgba(0, 0, 0, 0.3); border-radius: 10px; padding: 20px;")
        death_list_layout = QtWidgets.QVBoxLayout(self.death_list_container)
        death_list_layout.setSpacing(15)
        death_list_layout.setContentsMargins(20, 20, 20, 20)
        
        self.death_list_label = QtWidgets.QLabel("No one died last night.")
        self.death_list_label.setAlignment(QtCore.Qt.AlignCenter)
        self.death_list_label.setStyleSheet("""
            font-size: 24px;
            color: #2ecc71;
            font-weight: bold;
            padding: 20px;
        """)
        death_list_layout.addWidget(self.death_list_label)
        
        card_layout.addWidget(self.death_list_container)

        card_layout.addStretch()
        main_layout.addWidget(card)

    def update_death_list(self):
        """Cập nhật danh sách người chết"""
        if not self.dead_players:
            self.death_list_label.setText("No one died last night.")
            self.death_list_label.setStyleSheet("""
                font-size: 24px;
                color: #2ecc71;
                font-weight: bold;
                padding: 20px;
            """)
        else:
            # Hiển thị danh sách người chết
            death_text = "\n".join([f"💀 {username}" for username in self.dead_players])
            self.death_list_label.setText(death_text)
            self.death_list_label.setStyleSheet("""
                font-size: 20px;
                color: #e74c3c;
                font-weight: bold;
                padding: 20px;
            """)

    def start_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self):
        self.remaining -= 1
        if self.remaining > 0:
            self.timer_label.setText(f"⏱️ {self.remaining}s")
        else:
            self.timer.stop()
            self.on_timer_complete()

    def on_timer_complete(self):
        """Được gọi khi timer kết thúc - navigate sang day chat"""
        if self.window_manager:
            self.window_manager.navigate_to("day_chat")
        else:
            self.close()

    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()
    
    def on_logout(self):
        """Handle logout button click"""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout? You will leave the game.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                # Send logout request
                network_client = self.window_manager.get_shared_data("network_client") if self.window_manager else None
                if network_client:
                    network_client.send_packet(105, {})  # LOGOUT_REQ
                if self.toast_manager:
                    self.toast_manager.info("Logging out...")
                
                # Stop timer
                if hasattr(self, 'timer'):
                    self.timer.stop()
                
                # Clear shared data
                if self.window_manager:
                    self.window_manager.set_shared_data("user_id", None)
                    self.window_manager.set_shared_data("username", None)
                    self.window_manager.set_shared_data("current_room_id", None)
                    self.window_manager.set_shared_data("is_host", False)
                    self.window_manager.set_shared_data("connected", False)
                    # Navigate to welcome screen
                    self.window_manager.navigate_to("welcome")
                else:
                    self.close()

            except Exception as e:
                if self.toast_manager:
                    self.toast_manager.error(f"Logout error: {str(e)}")

