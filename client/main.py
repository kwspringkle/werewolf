# Main file để chạy ứng dụng Werewolf
import sys
import signal
from pathlib import Path
from PyQt5 import QtWidgets, QtCore

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from network_client import WerewolfNetworkClient
from components.toast_notification import ToastManager
from components.window_manager import WindowManager
from windows.welcome_window import WelcomeWindow
from windows.register_window import RegisterWindow
from windows.login_window import LoginWindow
from windows.lobby_window import LobbyWindow
from windows.room_window import RoomWindow
from windows.role_card_window import RoleCardWindow
from windows.night_begin_window import NightBeginWindow
from windows.death_announcement_window import DeathAnnouncementWindow
from windows.day_chat_window import DayChatWindow
from windows.day_vote_window import DayVoteWindow
from windows.game_result_window import GameResultWindow
from windows.roles.seer.seer_select_window import SeerSelectWindow
from windows.roles.seer.seer_wait_window import SeerWaitWindow
from windows.roles.seer.seer_result_window import SeerResultWindow
from windows.roles.guard.guard_select_window import GuardSelectWindow
from windows.roles.guard.guard_wait_window import GuardWaitWindow
from windows.roles.wolf.wolf_select_window import WolfSelectWindow
from windows.roles.wolf.wolf_wait_window import WolfWaitWindow
from windows.roles.wolf.wolf_chat_window import WolfChatWindow


class WerewolfApplication:    
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setApplicationName("Werewolf Game")
        # Prevent the whole client from exiting when transient night-phase dialogs close.
        # Otherwise, if all main windows are hidden and the last dialog closes, Qt will quit,
        # triggering cleanup() and disconnecting the socket (looks like "random disconnects").
        self.app.setQuitOnLastWindowClosed(False)

        # Graceful shutdown on Ctrl+C (SIGINT) / SIGTERM:
        # make sure we quit the Qt loop so aboutToQuit->cleanup runs and socket disconnects cleanly.
        self._install_signal_handlers()
        
        # Load stylesheet
        self.load_stylesheet()
        
        # Khởi tạo client 
        self.network_client = WerewolfNetworkClient()
        
        # Khởi tạo window manager
        self.window_manager = WindowManager(self.app)
        
        # Share network client với các cửa sổ
        self.window_manager.set_shared_data("network_client", self.network_client)
        
        # Khởi tạo các cửa sổ
        self.init_windows()
        
    def load_stylesheet(self):
        """Load QSS stylesheet"""
        qss_path = Path(__file__).parent / "assets" / "werewolf_theme.qss"
        
        if qss_path.exists():
            with open(qss_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
                self.app.setStyleSheet(stylesheet)
        else:
            print(f"Warning: Stylesheet not found at {qss_path}")
            
    def init_windows(self):
        """Khởi tạo tất cả các cửa sổ"""
        # Khởi tạo welcome window đầu tiên
        self.welcome_window = WelcomeWindow(
            self.network_client,
            None,  # toast_manager sẽ được tạo sau
            self.window_manager
        )
        
        # Tạo toast manager với welcome window làm parent
        self.toast_manager = ToastManager(self.welcome_window)

        # Share toast manager for any dynamically created windows (e.g., night role windows)
        self.window_manager.set_shared_data("toast_manager", self.toast_manager)
        
        # Cập nhật toast manager cho welcome window
        self.welcome_window.toast_manager = self.toast_manager
        
        self.register_window = RegisterWindow(
            self.toast_manager,
            self.window_manager
        )
        
        self.login_window = LoginWindow(
            self.toast_manager,
            self.window_manager
        )
        
        self.lobby_window = LobbyWindow(
            self.toast_manager,
            self.window_manager
        )
        
        self.room_window = RoomWindow(
            self.toast_manager,
            self.window_manager
        )
        
        self.role_card_window = RoleCardWindow(
            self.toast_manager,
            self.window_manager
        )

        self.night_begin_window = NightBeginWindow(
            self.toast_manager,
            self.window_manager
        )
        
        self.death_announcement_window = DeathAnnouncementWindow(
            self.toast_manager,
            self.window_manager
        )
        
        self.day_chat_window = DayChatWindow(
            self.toast_manager,
            self.window_manager
        )

        self.day_vote_window = DayVoteWindow(
            self.toast_manager,
            self.window_manager
        )

        self.game_result_window = GameResultWindow(
            self.toast_manager,
            self.window_manager
        )

        # Night role screens. These instances will be refreshed/overwritten by NightPhaseController as needed,
        # but registering defaults here avoids "window not registered" when navigating.
        self.window_manager.register_window("seer_select", SeerSelectWindow([], "", 30, None, None, window_manager=self.window_manager, toast_manager=self.toast_manager))
        self.window_manager.register_window("seer_wait", SeerWaitWindow(30, window_manager=self.window_manager, toast_manager=self.toast_manager))
        self.window_manager.register_window("seer_result", SeerResultWindow("", False, window_manager=self.window_manager, toast_manager=self.toast_manager))
        self.window_manager.register_window("guard_select", GuardSelectWindow([], "", 30, None, None, window_manager=self.window_manager, toast_manager=self.toast_manager))
        self.window_manager.register_window("guard_wait", GuardWaitWindow(30, window_manager=self.window_manager, toast_manager=self.toast_manager))
        self.window_manager.register_window("wolf_select", WolfSelectWindow([], [], "", 60, None, None, window_manager=self.window_manager, toast_manager=self.toast_manager))
        self.window_manager.register_window("wolf_wait", WolfWaitWindow(60, window_manager=self.window_manager, toast_manager=self.toast_manager))
        self.window_manager.register_window("wolf_chat", WolfChatWindow("", [], duration_seconds=60, window_manager=self.window_manager, toast_manager=self.toast_manager))
        
        # Đăng ký các cửa sổ
        self.window_manager.register_window("welcome", self.welcome_window)
        self.window_manager.register_window("register", self.register_window)
        self.window_manager.register_window("login", self.login_window)
        self.window_manager.register_window("lobby", self.lobby_window)
        self.window_manager.register_window("room", self.room_window)
        self.window_manager.register_window("role_card", self.role_card_window)
        self.window_manager.register_window("night_begin", self.night_begin_window)
        self.window_manager.register_window("death_announcement", self.death_announcement_window)
        self.window_manager.register_window("day_chat", self.day_chat_window)
        self.window_manager.register_window("day_vote", self.day_vote_window)
        self.window_manager.register_window("game_result", self.game_result_window)
        
        # Kết nối cleanup
        self.app.aboutToQuit.connect(self.cleanup)
        
    def run(self):
        """Chạy ứng dụng"""
        # Hiện cửa sổ welcome
        self.window_manager.navigate_to("welcome")
        
        # Bắt đầu vòng lặp sự kiện
        return self.app.exec_()

    def _install_signal_handlers(self):
        """Install SIGINT/SIGTERM handler so Ctrl+C in terminal closes the client cleanly."""
        # A small timer keeps the Python interpreter responsive to signals while Qt loop is running.
        self._signal_timer = QtCore.QTimer()
        self._signal_timer.start(250)
        self._signal_timer.timeout.connect(lambda: None)

        def _handle_sig(_signum, _frame):
            try:
                print("[DEBUG] Signal received, shutting down client...")
            except Exception:
                pass
            try:
                self.app.quit()
            except Exception:
                pass

        try:
            signal.signal(signal.SIGINT, _handle_sig)
        except Exception:
            pass
        try:
            signal.signal(signal.SIGTERM, _handle_sig)
        except Exception:
            pass
        
    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        try:
            if self.network_client:
                self.network_client.disconnect()
                self.network_client.destroy()
        except:
            pass


def main():
    """Main entry point"""
    app = WerewolfApplication()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
