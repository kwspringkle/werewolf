"""Connection Monitor - Theo dõi và xử lý mất kết nối"""

from PyQt5 import QtCore, QtWidgets
import time


class ConnectionMonitor(QtCore.QObject):
    """Monitor kết nối và xử lý reconnect"""
    
    connection_lost = QtCore.pyqtSignal()
    connection_restored = QtCore.pyqtSignal()
    
    def __init__(self, network_client, toast_manager, window_manager):
        super().__init__()
        self.network_client = network_client
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        
        self.last_pong_time = time.time()
        self.is_connected = True
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Timer kiểm tra connection
        self.check_timer = QtCore.QTimer()
        self.check_timer.timeout.connect(self.check_connection)
        
    def start(self):
        """Bắt đầu monitor"""
        self.last_pong_time = time.time()
        self.is_connected = True
        self.check_timer.start(5000)  # Check mỗi 5 giây
        
    def stop(self):
        """Dừng monitor"""
        self.check_timer.stop()
        
    def on_pong_received(self):
        """Gọi khi nhận được pong từ server"""
        self.last_pong_time = time.time()
        self.is_connected = True
        self.reconnect_attempts = 0
        
    def check_connection(self):
        """Kiểm tra trạng thái kết nối"""
        elapsed = time.time() - self.last_pong_time
        
        # Nếu không nhận pong trong 60 giây -> coi như mất kết nối
        if elapsed > 60 and self.is_connected:
            self.is_connected = False
            self.connection_lost.emit()
            self.handle_connection_lost()
            
    def handle_connection_lost(self):
        """Xử lý khi mất kết nối"""
        self.toast_manager.error("⚠️ Connection lost to server!")
        
        # Hiển thị dialog
        reply = QtWidgets.QMessageBox.question(
            None,
            "Connection Lost",
            "Lost connection to server.\nDo you want to try reconnecting?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.attempt_reconnect()
        else:
            self.return_to_welcome()
            
    def attempt_reconnect(self):
        """Thử kết nối lại"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.toast_manager.error("Failed to reconnect after multiple attempts")
            self.return_to_welcome()
            return
            
        self.reconnect_attempts += 1
        self.toast_manager.info(f"Reconnecting... (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
        
        try:
            # Lấy thông tin connection cũ
            host = self.window_manager.get_shared_data("server_host", "127.0.0.1")
            port = self.window_manager.get_shared_data("server_port", 5000)
            
            # Disconnect cũ
            try:
                self.network_client.disconnect()
            except:
                pass
                
            # Reconnect
            self.network_client.create()
            self.network_client.connect(host, port)

            self.is_connected = True
            self.last_pong_time = time.time()
            self.reconnect_attempts = 0  # Reset counter

            # Show success message
            self.toast_manager.success("Reconnected to server!")

            # Emit signal to restart timers
            self.connection_restored.emit()

            # Show info about re-login
            self.toast_manager.warning("Please login again to continue")
            
        except Exception as e:
            self.toast_manager.error(f"Reconnect failed: {str(e)}")
            
            # Retry sau 2^n giây (exponential backoff)
            delay = min(2 ** self.reconnect_attempts, 30) * 1000
            QtCore.QTimer.singleShot(delay, self.attempt_reconnect)
            
    def return_to_welcome(self):
        """Quay về màn hình welcome"""
        self.stop()
        
        # Clear all shared data
        self.window_manager.set_shared_data("user_id", None)
        self.window_manager.set_shared_data("username", None)
        self.window_manager.set_shared_data("current_room_id", None)
        
        # Navigate to welcome
        self.window_manager.navigate_to("welcome")