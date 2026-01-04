from PyQt5 import QtWidgets, QtCore
from components.user_header import UserHeader

class WolfWaitWindow(QtWidgets.QWidget):
    """Non-wolf players see this while Wolves are choosing, styled like RoleCardWindow"""
    def __init__(self, duration_seconds=30, parent=None, window_manager=None, toast_manager=None):
        super().__init__(parent)
        self.use_default_size = True
        self.preserve_window_flags = False
        self.duration = duration_seconds
        self.remaining = duration_seconds
        self.window_manager = window_manager
        self.toast_manager = toast_manager
        self.setObjectName("wolf_wait_window")
        self.setWindowTitle("Night — Wolves are choosing")
        self.setup_ui()
        self.start_timer()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        my_username = None
        if self.window_manager:
            my_username = self.window_manager.get_shared_data("username")
        self.user_header = UserHeader(self)
        self.user_header.set_username(my_username or "Player")
        self.user_header.logout_clicked.connect(self.on_logout)
        main_layout.addWidget(self.user_header)

        card = QtWidgets.QFrame()
        card.setObjectName("wolf_wait_card")
        card.setStyleSheet("""
            QFrame#wolf_wait_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 3px solid #e94560;
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

        icon_label = QtWidgets.QLabel("🐺")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 100px;")
        card_layout.addWidget(icon_label)

        title_label = QtWidgets.QLabel("The Werewolves are choosing a target...")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; color: #e94560; font-weight: bold;")
        card_layout.addWidget(title_label)

        subtitle = QtWidgets.QLabel("Please wait while the Werewolves perform their action.")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 16px; color: #cccccc; margin-top: 10px;")
        card_layout.addWidget(subtitle)

        card_layout.addStretch()
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
            if self.window_manager:
                nc = self.window_manager.get_shared_data("network_client")
                if nc:
                    try:
                        nc.send_packet(208, {})
                    except Exception:
                        pass
                    try:
                        nc.send_packet(105, {})
                    except Exception:
                        pass
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
        if self.remaining > 0:
            self.timer_label.setText(f"⏱️ {self.remaining}s")
        else:
            self.timer.stop()
            self.close()

    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()

