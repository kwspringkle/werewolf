from PyQt5 import QtWidgets, QtCore
try:
    from utils.image_utils import create_image_icon_label
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))
    from image_utils import create_image_icon_label

class SeerResultWindow(QtWidgets.QWidget):
    """Show seer result styled like RoleCardWindow"""
    def __init__(self, target_username, is_werewolf, parent=None):
        super().__init__(parent)
        # Regular window with standard controls
        self.use_default_size = True
        self.preserve_window_flags = False
        self.setObjectName("seer_result_window")
        self.setWindowTitle("Seer Result")
        self.resize(500, 600)
        self.setup_ui(target_username, is_werewolf)

    def setup_ui(self, target_username, is_werewolf):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        card = QtWidgets.QFrame()
        card.setObjectName("seer_result_card")
        card.setStyleSheet("""
            QFrame#seer_result_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 3px solid #3a86ff;
                border-radius: 15px;
            }
        """)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(30)
        card_layout.setContentsMargins(30, 30, 30, 30)

        # Render ảnh thay vì emoji
        if is_werewolf:
            icon_label = create_image_icon_label("is_werewolf.png", size=180)
        else:
            icon_label = create_image_icon_label("is_not_werewolf.png", size=180)
        card_layout.addWidget(icon_label)

        title = QtWidgets.QLabel(f"{target_username}")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size:28px; font-weight:bold; color:#fff;")
        card_layout.addWidget(title)

        subtitle = "IS A WEREWOLF" if is_werewolf else "IS NOT A WEREWOLF"
        subtitle_lbl = QtWidgets.QLabel(subtitle)
        subtitle_lbl.setAlignment(QtCore.Qt.AlignCenter)
        if is_werewolf:
            subtitle_lbl.setStyleSheet("font-size:20px; color:#e94560; font-weight:bold;")
        else:
            subtitle_lbl.setStyleSheet("font-size:20px; color:#3a86ff; font-weight:bold;")
        card_layout.addWidget(subtitle_lbl)

        card_layout.addStretch()

        btn = QtWidgets.QPushButton("OK")
        btn.setStyleSheet("font-size:18px; padding:10px 30px; border-radius:8px; background:#3a86ff; color:white;")
        btn.clicked.connect(self.close)
        card_layout.addWidget(btn, alignment=QtCore.Qt.AlignCenter)

        main_layout.addWidget(card)

    def closeEvent(self, event):
        event.accept()
