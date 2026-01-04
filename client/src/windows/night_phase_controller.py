
from PyQt5 import QtCore, QtWidgets
from .roles.seer.seer_select_window import SeerSelectWindow
from .roles.seer.seer_result_window import SeerResultWindow
from .roles.seer.seer_wait_window import SeerWaitWindow
from .roles.guard.guard_select_window import GuardSelectWindow
from .roles.guard.guard_wait_window import GuardWaitWindow
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
            print(f"[DEBUG] Seer select - players list: {[p.get('username', 'unknown') for p in self.players]}")
            print(f"[DEBUG] Seer select - total players: {len(self.players)}")
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
            print(f"[DEBUG] Guard select - players list: {[p.get('username', 'unknown') if isinstance(p, dict) else str(p) for p in self.players]}")
            print(f"[DEBUG] Guard select - total players: {len(self.players)}")
            print(f"[DEBUG] Guard select - full players data: {self.players}")
            # Đảm bảo truyền TẤT CẢ players vào GuardSelectWindow, không filter
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
        
        # Filter: chỉ lấy những người KHÔNG phải sói và không phải chính mình
        player_list = []
        alive_status = []
        for p in self.players:
            username = p.get('username', '')
            # Bỏ qua chính mình và những người trong wolf team
            if username != self.my_username and username not in self.wolf_usernames:
                player_list.append(username)
                alive_status.append(p.get('is_alive', 1))
        
        print(f"[DEBUG] Wolf select - filtered players (non-wolves): {player_list}")
        print(f"[DEBUG] Wolf select - alive status: {alive_status}")
        
        # Debug: Print detailed info about wolf detection
        print(f"[DEBUG] Wolf phase check - is_wolf: {self.is_wolf}, my_username: {self.my_username}")
        print(f"[DEBUG] Wolf usernames: {self.wolf_usernames}")
        print(f"[DEBUG] All players: {[p.get('username') for p in self.players]}")
        
        # Double-check: if my_username is in wolf_usernames, then is_wolf should be True
        if self.my_username in self.wolf_usernames:
            if not self.is_wolf:
                print(f"[WARNING] my_username {self.my_username} is in wolf_usernames but is_wolf is False! Fixing...")
                self.is_wolf = True
        
        if self.is_wolf:
            print("[DEBUG] User is wolf - showing WolfSelectWindow")
            from .roles.wolf.wolf_select_window import WolfSelectWindow
            from .roles.wolf.wolf_chat_window import WolfChatWindow
            
            # Tạo WolfSelectWindow trực tiếp
            self.wolf_controller = WolfSelectWindow(
                player_list, alive_status, self.my_username, 
                duration_seconds=self.wolf_duration,
                network_client=self.network_client, room_id=self.room_id
            )
            
            # Tạo chat window và connect button
            self.wolf_chat_window = None
            def show_chat():
                if not self.wolf_chat_window:
                    # Create send callback for wolf chat
                    def send_wolf_chat(message):
                        try:
                            if self.network_client and self.room_id:
                                payload = {
                                    "room_id": self.room_id,
                                    "message": message
                                }
                                self.network_client.send_packet(401, payload)  # CHAT_REQ
                                print(f"[DEBUG] Sent wolf chat: {message}")
                        except Exception as e:
                            print(f"[ERROR] Failed to send wolf chat: {e}")

                    self.wolf_chat_window = WolfChatWindow(
                        self.my_username, self.wolf_usernames,
                        send_callback=send_wolf_chat,
                        duration_seconds=getattr(self.wolf_controller, "remaining", self.wolf_duration),
                        network_client=self.network_client,
                        room_id=self.room_id
                    )
                    self.wolf_chat_window.setWindowModality(QtCore.Qt.ApplicationModal)
                    # Center chat window
                    screen = QtWidgets.QApplication.desktop().screenGeometry()
                    window_geometry = self.wolf_chat_window.frameGeometry()
                    window_geometry.moveCenter(screen.center())
                    self.wolf_chat_window.move(window_geometry.topLeft())
                    # Button để quay lại select window
                    if hasattr(self.wolf_chat_window, 'switch_btn'):
                        self.wolf_chat_window.switch_btn.clicked.connect(show_select)
                self.wolf_controller.hide()
                # Sync countdown each time chat is opened (share the same remaining time)
                if hasattr(self.wolf_chat_window, "sync_remaining"):
                    self.wolf_chat_window.sync_remaining(getattr(self.wolf_controller, "remaining", self.wolf_duration))
                self.wolf_chat_window.show()
                self.wolf_chat_window.raise_()
                self.wolf_chat_window.activateWindow()
            
            def show_select():
                if self.wolf_chat_window:
                    self.wolf_chat_window.hide()
                self.wolf_controller.show()
                self.wolf_controller.raise_()
                self.wolf_controller.activateWindow()
            
            # Connect chat button
            if hasattr(self.wolf_controller, 'chat_btn'):
                self.wolf_controller.chat_btn.clicked.connect(show_chat)
            
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
