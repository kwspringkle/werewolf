from PyQt5 import QtWidgets, QtCore
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.user_header import UserHeader

class NightBeginWindow(QtWidgets.QWidget):
    """Night begin screen styled like RoleCardWindow, with countdown"""
    def __init__(self, toast_manager=None, window_manager=None):
        super().__init__()
        # Normal window (movable, consistent sizing via WindowManager)
        self.use_default_size = True
        self.preserve_window_flags = False
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.duration = 30
        self.remaining = 30
        self.deadline = None
        self.timer = None
        self.setObjectName("night_begin_window")
        self.setWindowTitle("Night Begins")
        self.setup_ui()
        
    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)
        # Set username cho user_header
        username = self.window_manager.get_shared_data("username", "Player")
        self.user_header.set_username(username)
        # Prefer shared deadline for stable sync
        shared_deadline = self.window_manager.get_shared_data("night_begin_deadline")
        if shared_deadline is None:
            remaining_time = self.window_manager.get_shared_data("night_begin_remaining_time", 30)
            shared_deadline = time.time() + float(remaining_time)
            self.window_manager.set_shared_data("night_begin_deadline", shared_deadline)

        self.deadline = shared_deadline
        self.remaining = max(0, int(self.deadline - time.time()))
        self.timer_label.setText(f"⏱️ {self.remaining}s")
        if self.remaining > 0:
            self.start_timer()
        else:
            # Don't auto-close; wait for PHASE_NIGHT to be handled by RoomWindow
            self.accept_or_close()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # User header (username + logout)
        self.user_header = UserHeader(self)
        self.user_header.logout_clicked.connect(self.on_logout)
        main_layout.addWidget(self.user_header)

        card = QtWidgets.QFrame()
        card.setObjectName("night_card")
        card.setStyleSheet("""
            QFrame#night_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 3px solid #3a86ff;
                border-radius: 15px;
            }
        """)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(30)
        card_layout.setContentsMargins(30, 30, 30, 30)

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

        icon_label = QtWidgets.QLabel("🌙")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 120px;")
        card_layout.addWidget(icon_label)

        title_label = QtWidgets.QLabel("NIGHT FALLS")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 36px;
            color: #3a86ff;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        card_layout.addWidget(title_label)

        subtitle = QtWidgets.QLabel("Everyone go to sleep.")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 16px; color: #cccccc; margin-top: 10px;")
        card_layout.addWidget(subtitle)

        card_layout.addStretch()
        main_layout.addWidget(card)

    def start_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self):
        if self.deadline is not None:
            self.remaining = max(0, int(self.deadline - time.time()))
        else:
            self.remaining = max(0, self.remaining - 1)

        if self.remaining > 0:
            self.timer_label.setText(f"⏱️ {self.remaining}s")
        else:
            self.timer.stop()
            self.accept_or_close()

    def accept_or_close(self):
        # Không tự động đóng - sẽ đợi PHASE_NIGHT từ server
        # Window này sẽ được đóng bởi room_window khi nhận PHASE_NIGHT
        pass

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
                network_client = self.window_manager.get_shared_data("network_client")
                if network_client:
                    network_client.send_packet(105, {})  # LOGOUT_REQ
                if self.toast_manager:
                    self.toast_manager.info("Logging out...")
                
                # Stop timer
                if hasattr(self, 'timer'):
                    self.timer.stop()
                
                # Clear shared data
                self.window_manager.set_shared_data("user_id", None)
                self.window_manager.set_shared_data("username", None)
                self.window_manager.set_shared_data("current_room_id", None)
                self.window_manager.set_shared_data("is_host", False)
                self.window_manager.set_shared_data("connected", False)

                # Navigate to welcome screen
                self.window_manager.navigate_to("welcome")

            except Exception as e:
                if self.toast_manager:
                    self.toast_manager.error(f"Logout error: {str(e)}")
