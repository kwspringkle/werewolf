from PyQt5 import QtWidgets, QtCore

class SeerWaitWindow(QtWidgets.QWidget):
    """Non-seer players see this while Seer is choosing, styled like RoleCardWindow"""
    def __init__(self, duration_seconds=30, parent=None):
        super().__init__(parent)
        # Regular window with standard controls
        self.use_default_size = True
        self.preserve_window_flags = False
        self.duration = duration_seconds
        self.remaining = duration_seconds
        self.setObjectName("seer_wait_window")
        self.setWindowTitle("Night — Seer is choosing")
        self.resize(500, 600)
        self.setup_ui()
        self.start_timer()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        card = QtWidgets.QFrame()
        card.setObjectName("seer_wait_card")
        card.setStyleSheet("""
            QFrame#seer_wait_card {
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

        icon_label = QtWidgets.QLabel("🔮")
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 100px;")
        card_layout.addWidget(icon_label)

        title_label = QtWidgets.QLabel("The Seer is checking a player...")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; color: #3a86ff; font-weight: bold;")
        card_layout.addWidget(title_label)

        subtitle = QtWidgets.QLabel("Please wait while the Seer performs their action.")
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
            self.close()

    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()
