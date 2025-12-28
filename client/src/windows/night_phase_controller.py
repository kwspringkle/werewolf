
from PyQt5 import QtCore
from .roles.seer.seer_select_window import SeerSelectWindow
from .roles.seer.seer_result_window import SeerResultWindow
from .roles.seer.seer_wait_window import SeerWaitWindow
from .roles.guard.guard_select_window import GuardSelectWindow
from .roles.guard.guard_wait_window import GuardWaitWindow
from .roles.wolf.wolf_phase_controller import WolfPhaseController


class NightPhaseController:
    """Điều phối night phase: seer -> guard -> wolf (role-based windows)"""
    def __init__(self, window_manager, network_client, players, my_username, room_id, is_seer, is_guard, is_wolf, wolf_usernames, duration=30):
        self.window_manager = window_manager
        self.network_client = network_client
        self.players = players
        self.my_username = my_username
        self.room_id = room_id
        self.is_seer = is_seer
        self.is_guard = is_guard
        self.is_wolf = is_wolf
        self.wolf_usernames = wolf_usernames
        self.duration = duration
        self.seer_window = None
        self.guard_window = None
        self.wolf_controller = None

    def start(self):
        self.start_seer_phase()

    def start_seer_phase(self):
        if self.is_seer:
            self.seer_window = SeerSelectWindow(self.players, self.my_username, self.duration, self.network_client, self.room_id)
            self.seer_window.setWindowModality(QtCore.Qt.ApplicationModal)
            self.seer_window.show()
            self.seer_window.raise_()
            self.seer_window.activateWindow()
            self.seer_window.destroyed.connect(self._on_seer_select_closed)
        else:
            self.seer_window = SeerWaitWindow(self.duration)
            self.seer_window.setWindowModality(QtCore.Qt.ApplicationModal)
            self.seer_window.show()
            self.seer_window.raise_()
            self.seer_window.activateWindow()
            QtCore.QTimer.singleShot(self.duration * 1000, self._on_seer_select_closed)

    def _on_seer_select_closed(self):
        # If seer, show result window (simulate result for now)
        if self.is_seer:
            # TODO: Replace with actual result from server/network
            # For now, just show a dummy result window for 2 seconds
            result_win = SeerResultWindow("dummy_user", False)
            result_win.setWindowModality(QtCore.Qt.ApplicationModal)
            result_win.show()
            QtCore.QTimer.singleShot(2000, result_win.close)
            result_win.destroyed.connect(self.start_guard_phase)
        else:
            self.start_guard_phase()

    def start_guard_phase(self):
        if self.is_guard:
            self.guard_window = GuardSelectWindow(self.players, self.my_username, self.duration, self.network_client, self.room_id)
            self.guard_window.setWindowModality(QtCore.Qt.ApplicationModal)
            self.guard_window.show()
            self.guard_window.raise_()
            self.guard_window.activateWindow()
            self.guard_window.destroyed.connect(self.start_wolf_phase)
        else:
            self.guard_window = GuardWaitWindow(self.duration)
            self.guard_window.setWindowModality(QtCore.Qt.ApplicationModal)
            self.guard_window.show()
            self.guard_window.raise_()
            self.guard_window.activateWindow()
            QtCore.QTimer.singleShot(self.duration * 1000, self.start_wolf_phase)

    def start_wolf_phase(self):
        player_list = [p['username'] for p in self.players if p['username'] != self.my_username]
        alive_status = [p.get('is_alive', 1) for p in self.players if p['username'] != self.my_username]
        self.wolf_controller = WolfPhaseController(
            player_list, alive_status, self.my_username, self.wolf_usernames,
            network_client=self.network_client, room_id=self.room_id, duration_seconds=self.duration
        )
        self.wolf_controller.setWindowModality(QtCore.Qt.ApplicationModal)
        self.wolf_controller.show()
        self.wolf_controller.raise_()
        self.wolf_controller.activateWindow()
