from PyQt5 import QtWidgets, QtCore

class NightBeginWindow(QtWidgets.QWidget):
    """Night begin screen styled like RoleCardWindow, with countdown"""
    def __init__(self, toast_manager=None, window_manager=None):
        super().__init__()
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.duration = 30
        self.remaining = 30
        self.timer = None
        self.setObjectName("night_begin_window")
        self.setWindowTitle("Night Begins")
        self.setFixedSize(600, 500)  # Set fixed size để tránh window trắng
        self.setup_ui()
        
    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)
        # Lấy remaining_time từ shared data
        remaining_time = self.window_manager.get_shared_data("night_begin_remaining_time", 30)
        self.duration = remaining_time
        self.remaining = remaining_time
        self.timer_label.setText(f"⏱️ {self.remaining}s")
        self.start_timer()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

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
        self.remaining -= 1
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
