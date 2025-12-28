
from PyQt5 import QtCore, QtWidgets
from .roles.seer.seer_select_window import SeerSelectWindow
from .roles.seer.seer_result_window import SeerResultWindow
from .roles.seer.seer_wait_window import SeerWaitWindow
from .roles.guard.guard_select_window import GuardSelectWindow
from .roles.guard.guard_wait_window import GuardWaitWindow
from .roles.wolf.wolf_phase_controller import WolfPhaseController
from .roles.wolf.wolf_wait_window import WolfWaitWindow


class NightPhaseController:
    """Điều phối night phase: seer -> guard -> wolf (role-based windows)"""
    def __init__(self, window_manager, network_client, players, my_username, room_id, is_seer, is_guard, is_wolf, wolf_usernames, seer_duration=30, guard_duration=30, wolf_duration=30):
        self.window_manager = window_manager
        self.network_client = network_client
        self.players = players
        self.my_username = my_username
        self.room_id = room_id
        self.is_seer = is_seer
        self.is_guard = is_guard
        self.is_wolf = is_wolf
        self.wolf_usernames = wolf_usernames
        self.seer_duration = seer_duration
        self.guard_duration = guard_duration
        self.wolf_duration = wolf_duration
        self.seer_window = None
        self.seer_result_window = None
        self.guard_window = None
        self.wolf_controller = None
        self.seer_choice_made = False
        self.guard_phase_started = False  # Flag để tránh chuyển phase nhiều lần
        self.wolf_phase_started = False   # Flag để tránh chuyển phase nhiều lần
        print(f"[DEBUG] NightPhaseController initialized - seer: {self.is_seer}, guard: {self.is_guard}, wolf: {self.is_wolf}")
        print(f"[DEBUG] Phase durations - seer: {self.seer_duration}s, guard: {self.guard_duration}s, wolf: {self.wolf_duration}s")

    def start(self):
        print("[DEBUG] Starting seer phase...")
        self.start_seer_phase()

    def start_seer_phase(self):
        if self.is_seer:
            print("[DEBUG] User is seer - creating and showing SeerSelectWindow")
            try:
                self.seer_window = SeerSelectWindow(self.players, self.my_username, self.seer_duration, self.network_client, self.room_id)
                self.seer_window.setWindowModality(QtCore.Qt.ApplicationModal)
                # Center the window on screen
                screen = QtWidgets.QApplication.desktop().screenGeometry()
                window_geometry = self.seer_window.frameGeometry()
                window_geometry.moveCenter(screen.center())
                self.seer_window.move(window_geometry.topLeft())
                # Show window with all flags to ensure it's visible
                self.seer_window.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
                self.seer_window.show()
                self.seer_window.raise_()
                self.seer_window.activateWindow()
                print("[DEBUG] SeerSelectWindow shown successfully")
                # Force focus after a short delay to ensure it's on top
                QtCore.QTimer.singleShot(100, lambda: (
                    self.seer_window.raise_(),
                    self.seer_window.activateWindow()
                ))
                # Connect to handle when seer makes choice or skips
                # Note: seer_select_window will send SEER_CHECK_REQ, then wait for SEER_RESULT (406)
                # When SEER_RESULT arrives, handle_seer_result will be called
                # If seer skips or times out, the window will close and trigger destroyed signal
                self.seer_window.destroyed.connect(self._on_seer_window_closed)
            except Exception as e:
                print(f"[ERROR] Failed to show SeerSelectWindow: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("[DEBUG] User is not seer - creating and showing SeerWaitWindow")
            try:
                self.seer_window = SeerWaitWindow(self.seer_duration)
                self.seer_window.setWindowModality(QtCore.Qt.ApplicationModal)
                # Center the window on screen
                screen = QtWidgets.QApplication.desktop().screenGeometry()
                window_geometry = self.seer_window.frameGeometry()
                window_geometry.moveCenter(screen.center())
                self.seer_window.move(window_geometry.topLeft())
                # Show window with all flags to ensure it's visible
                self.seer_window.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
                self.seer_window.show()
                self.seer_window.raise_()
                self.seer_window.activateWindow()
                print("[DEBUG] SeerWaitWindow shown successfully")
                # Force focus after a short delay to ensure it's on top
                QtCore.QTimer.singleShot(100, lambda: (
                    self.seer_window.raise_(),
                    self.seer_window.activateWindow()
                ))
                # For non-seer players, wait for seer_duration then move to guard phase
                QtCore.QTimer.singleShot(self.seer_duration * 1000, self._on_seer_phase_timeout)
            except Exception as e:
                print(f"[ERROR] Failed to show SeerWaitWindow: {e}")
                import traceback
                traceback.print_exc()

    def _on_seer_window_closed(self):
        """Called when seer select window is closed (either by choice or skip)"""
        print("[DEBUG] Seer window closed")
        # If seer made a choice, wait for result from server (handle_seer_result will be called)
        # If seer skipped or timed out, move to guard phase
        if not self.seer_choice_made:
            print("[DEBUG] Seer skipped or timed out, moving to guard phase...")
            self.seer_window = None
            self.start_guard_phase()
    
    def _on_seer_phase_timeout(self):
        """Called when seer phase timeout (for non-seer players)"""
        print("[DEBUG] Seer phase timeout, moving to guard phase...")
        if self.seer_window:
            self.seer_window.close()
        self.start_guard_phase()
    
    def handle_seer_result(self, target_username, is_werewolf):
        """Handle SEER_RESULT packet from server"""
        print(f"[DEBUG] Received seer result - target: {target_username}, is_werewolf: {is_werewolf}")
        self.seer_choice_made = True
        
        # Close seer select window if still open
        if self.seer_window:
            self.seer_window.close()
            self.seer_window = None
        
        # Show result window
        self.seer_result_window = SeerResultWindow(target_username, is_werewolf)
        self.seer_result_window.setWindowModality(QtCore.Qt.ApplicationModal)
        # Center the window on screen
        screen = QtWidgets.QApplication.desktop().screenGeometry()
        window_geometry = self.seer_result_window.frameGeometry()
        window_geometry.moveCenter(screen.center())
        self.seer_result_window.move(window_geometry.topLeft())
        self.seer_result_window.show()
        self.seer_result_window.raise_()
        self.seer_result_window.activateWindow()
        # Force focus after a short delay
        QtCore.QTimer.singleShot(100, lambda: self.seer_result_window.activateWindow())
        
        # When result window is closed (OK button clicked), move to guard phase immediately
        # Connect to the OK button's clicked signal instead of destroyed
        # Find the OK button and connect it
        for widget in self.seer_result_window.findChildren(QtWidgets.QPushButton):
            if widget.text() == "OK":
                widget.clicked.connect(self._on_seer_result_closed)
                break
        
        # Also connect destroyed as fallback
        self.seer_result_window.destroyed.connect(self._on_seer_result_closed)
    
    def _on_seer_result_closed(self):
        """Called when seer result window is closed"""
        print("[DEBUG] Seer result window closed")
        if self.seer_result_window:
            self.seer_result_window = None
        # Không tự động chuyển sang guard phase - đợi server broadcast PHASE_GUARD_START
        # Nếu server đã broadcast thì guard_phase_started sẽ là True
        if not self.guard_phase_started:
            print("[DEBUG] Waiting for PHASE_GUARD_START from server...")
        else:
            print("[DEBUG] Guard phase already started, skipping")

    def start_guard_phase(self):
        # Tránh chuyển phase nhiều lần
        if self.guard_phase_started:
            print("[DEBUG] Guard phase already started, skipping...")
            return
        
        print("[DEBUG] Starting guard phase...")
        self.guard_phase_started = True
        
        # Close seer windows if still open
        if self.seer_result_window:
            self.seer_result_window.close()
            self.seer_result_window = None
        if self.seer_window:
            self.seer_window.close()
            self.seer_window = None
        
        if self.is_guard:
            print("[DEBUG] User is guard - showing GuardSelectWindow")
            self.guard_window = GuardSelectWindow(self.players, self.my_username, self.guard_duration, self.network_client, self.room_id)
            self.guard_window.setWindowModality(QtCore.Qt.ApplicationModal)
            # Center the window on screen
            screen = QtWidgets.QApplication.desktop().screenGeometry()
            window_geometry = self.guard_window.frameGeometry()
            window_geometry.moveCenter(screen.center())
            self.guard_window.move(window_geometry.topLeft())
            self.guard_window.show()
            self.guard_window.raise_()
            self.guard_window.activateWindow()
            QtCore.QTimer.singleShot(100, lambda: self.guard_window.activateWindow())
            # Guard window sẽ tự đóng khi guard chọn xong, nhưng không tự động chuyển sang wolf
            # Đợi server broadcast PHASE_WOLF_START (không connect destroyed signal)
        else:
            print("[DEBUG] User is not guard - showing GuardWaitWindow")
            self.guard_window = GuardWaitWindow(self.guard_duration)
            self.guard_window.setWindowModality(QtCore.Qt.ApplicationModal)
            # Center the window on screen
            screen = QtWidgets.QApplication.desktop().screenGeometry()
            window_geometry = self.guard_window.frameGeometry()
            window_geometry.moveCenter(screen.center())
            self.guard_window.move(window_geometry.topLeft())
            self.guard_window.show()
            self.guard_window.raise_()
            self.guard_window.activateWindow()
            QtCore.QTimer.singleShot(100, lambda: self.guard_window.activateWindow())
            # Không tự động chuyển sang wolf phase - đợi server broadcast PHASE_WOLF_START
            # Timer chỉ để đóng window nếu cần

    def start_wolf_phase(self):
        # Tránh chuyển phase nhiều lần
        if self.wolf_phase_started:
            print("[DEBUG] Wolf phase already started, skipping...")
            return
        
        print("[DEBUG] Starting wolf phase...")
        self.wolf_phase_started = True
        
        # Close guard window if still open
        if self.guard_window:
            self.guard_window.close()
            self.guard_window = None
        
        player_list = [p['username'] for p in self.players if p['username'] != self.my_username]
        alive_status = [p.get('is_alive', 1) for p in self.players if p['username'] != self.my_username]
        
        if self.is_wolf:
            print("[DEBUG] User is wolf - showing WolfPhaseController")
            self.wolf_controller = WolfPhaseController(
                player_list, alive_status, self.my_username, self.wolf_usernames,
                network_client=self.network_client, room_id=self.room_id, duration_seconds=self.wolf_duration
            )
            self.wolf_controller.setWindowModality(QtCore.Qt.ApplicationModal)
            # Center the window on screen
            screen = QtWidgets.QApplication.desktop().screenGeometry()
            window_geometry = self.wolf_controller.frameGeometry()
            window_geometry.moveCenter(screen.center())
            self.wolf_controller.move(window_geometry.topLeft())
            self.wolf_controller.show()
            self.wolf_controller.raise_()
            self.wolf_controller.activateWindow()
            QtCore.QTimer.singleShot(100, lambda: self.wolf_controller.activateWindow())
        else:
            print("[DEBUG] User is not wolf - showing WolfWaitWindow")
            self.wolf_controller = WolfWaitWindow(self.wolf_duration)
            self.wolf_controller.setWindowModality(QtCore.Qt.ApplicationModal)
            # Center the window on screen
            screen = QtWidgets.QApplication.desktop().screenGeometry()
            window_geometry = self.wolf_controller.frameGeometry()
            window_geometry.moveCenter(screen.center())
            self.wolf_controller.move(window_geometry.topLeft())
            self.wolf_controller.show()
            self.wolf_controller.raise_()
            self.wolf_controller.activateWindow()
            QtCore.QTimer.singleShot(100, lambda: self.wolf_controller.activateWindow())
            # Không tự động đóng - sẽ đợi server broadcast phase tiếp theo hoặc đóng khi nhận signal
