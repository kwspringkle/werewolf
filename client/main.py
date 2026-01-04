# Main file để chạy ứng dụng Werewolf
import sys
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


class WerewolfApplication:    
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setApplicationName("Werewolf Game")
        # Prevent the whole client from exiting when transient night-phase dialogs close.
        # Otherwise, if all main windows are hidden and the last dialog closes, Qt will quit,
        # triggering cleanup() and disconnecting the socket (looks like "random disconnects").
        self.app.setQuitOnLastWindowClosed(False)
        
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
        
        # Kết nối cleanup
        self.app.aboutToQuit.connect(self.cleanup)
        
    def run(self):
        """Chạy ứng dụng"""
        # Hiện cửa sổ welcome
        self.window_manager.navigate_to("welcome")
        
        # Bắt đầu vòng lặp sự kiện
        return self.app.exec_()
        
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
