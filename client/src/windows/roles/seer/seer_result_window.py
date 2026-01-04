from PyQt5 import QtWidgets, QtCore
from components.user_header import UserHeader
try:
    from utils.image_utils import create_image_icon_label
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))
    from image_utils import create_image_icon_label

class SeerResultWindow(QtWidgets.QWidget):
    """Màn hình kết quả của Seer"""
    def __init__(self, target_username, is_werewolf, parent=None, window_manager=None, toast_manager=None):
        super().__init__(parent)
        self.use_default_size = True
        self.preserve_window_flags = False
        self.window_manager = window_manager
        self.toast_manager = toast_manager
        self.setObjectName("seer_result_window")
        self.setWindowTitle("Seer Result")
        self.setup_ui(target_username, is_werewolf)

    def setup_ui(self, target_username, is_werewolf):
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

    def closeEvent(self, event):
        event.accept()
