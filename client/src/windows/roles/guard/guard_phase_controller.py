from PyQt5 import QtWidgets, QtCore
from .guard_select_window import GuardSelectWindow
from .guard_wait_window import GuardWaitWindow

class GuardPhaseController:
    """Controller to handle guard phase UI and logic"""
    def __init__(self, window_manager, network_client, players, my_username, room_id, is_guard, duration=30):
        self.window_manager = window_manager
        self.network_client = network_client
        self.players = players
        self.my_username = my_username
        self.room_id = room_id
        self.is_guard = is_guard
        self.duration = duration
        self.guard_window = None

    def start(self):
        if self.is_guard:
            self.guard_window = GuardSelectWindow(
                self.players, self.my_username, self.duration,
                network_client=self.network_client, room_id=self.room_id
            )
        else:
            self.guard_window = GuardWaitWindow(self.duration)
        self.guard_window.setWindowModality(QtCore.Qt.ApplicationModal)
        self.guard_window.show()
        self.guard_window.raise_()
        self.guard_window.activateWindow()
