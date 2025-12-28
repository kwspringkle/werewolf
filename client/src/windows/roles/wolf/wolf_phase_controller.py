from PyQt5 import QtWidgets, QtCore
from .wolf_select_window import WolfSelectWindow
from .wolf_chat_window import WolfChatWindow

class WolfPhaseController(QtWidgets.QWidget):
    """Controller cho phase sói: vote + chat"""
    def __init__(self, player_list, alive_status, my_username, wolf_usernames, network_client=None, room_id=None, duration_seconds=30, parent=None):
        super().__init__(parent)
        self.player_list = player_list
        self.alive_status = alive_status
        self.my_username = my_username
        self.wolf_usernames = wolf_usernames
        self.network_client = network_client
        self.room_id = room_id
        self.duration = duration_seconds
        self.vote_window = None
        self.chat_window = None
        self.init_vote_window()

    def init_vote_window(self):
        self.vote_window = WolfSelectWindow(self.player_list, self.alive_status, my_username=self.my_username, parent=self)
        self.vote_window.setWindowTitle("Sói chọn nạn nhân")
        # Use built-in chat icon if available, otherwise fall back to adding a bottom button
        if hasattr(self.vote_window, 'chat_btn'):
            self.vote_window.chat_btn.clicked.connect(self.show_chat_window)
        else:
            chat_btn = QtWidgets.QPushButton("Chat với sói")
            self.vote_window.layout().addWidget(chat_btn)
            chat_btn.clicked.connect(self.show_chat_window)
        # Xử lý xác nhận vote
        orig_accept = self.vote_window.accept
        def on_accept():
            target = self.vote_window.get_selected_username()
            if not target:
                QtWidgets.QMessageBox.warning(self, "Chọn nạn nhân", "Hãy chọn một người để cắn!")
                return
            if self.network_client and self.room_id is not None:
                try:
                    self.network_client.send_wolf_kill(self.room_id, target)
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Network", f"Gửi vote sói thất bại: {e}")
            orig_accept()
            self.close()
        self.vote_window.accept = on_accept
        self.vote_window.show()

    def show_chat_window(self):
        if not self.chat_window:
            self.chat_window = WolfChatWindow(self.my_username, self.wolf_usernames, parent=self)
            self.chat_window.switch_btn.clicked.connect(self.show_vote_window)
        self.vote_window.hide()
        self.chat_window.show()

    def show_vote_window(self):
        self.chat_window.hide()
        self.vote_window.show()
