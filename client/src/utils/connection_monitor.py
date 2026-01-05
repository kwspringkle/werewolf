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

        # Heartbeat tuning
        # Server pings periodically, but during gameplay the client may still be receiving other packets.
        # Treat any inbound traffic as "activity" and use a more tolerant timeout to avoid false disconnects.
        self.check_interval_ms = 10_000
        self.pong_timeout_seconds = 180

        # Optional client-initiated ping (in addition to server->client ping).
        # Helps detect half-open connections where no packets arrive.
        self.ping_interval_ms = 25_000
        
        # Timer kiểm tra connection
        self.check_timer = QtCore.QTimer()
        self.check_timer.timeout.connect(self.check_connection)

        self.ping_timer = QtCore.QTimer()
        self.ping_timer.timeout.connect(self.send_ping)
        
    def start(self):
        """Bắt đầu monitor"""
        self.last_pong_time = time.time()
        self.is_connected = True
        self.check_timer.start(self.check_interval_ms)
        self.ping_timer.start(self.ping_interval_ms)
        
    def stop(self):
        """Dừng monitor"""
        self.check_timer.stop()
        self.ping_timer.stop()

    def send_ping(self):
        """Gửi ping định kỳ để keepalive / detect dead links."""
        if not self.is_connected:
            return
        try:
            if hasattr(self.network_client, "send_ping"):
                self.network_client.send_ping()
        except Exception:
            # If sending fails, connection is likely broken.
            if self.is_connected:
                self.is_connected = False
                self.connection_lost.emit()
                self.handle_connection_lost()
        
    def on_pong_received(self):
        """Gọi khi nhận được pong từ server"""
        self.last_pong_time = time.time()
        self.is_connected = True
        self.reconnect_attempts = 0

    def on_activity(self):
        """Gọi khi nhận được bất kỳ packet nào từ server (treat as alive)."""
        self.on_pong_received()
        
    def check_connection(self):
        """Kiểm tra trạng thái kết nối"""
        elapsed = time.time() - self.last_pong_time
        
        # Nếu không nhận activity trong một khoảng thời gian -> coi như mất kết nối
        if elapsed > self.pong_timeout_seconds and self.is_connected:
            try:
                print(f"[DEBUG] ConnectionMonitor: no activity for {int(elapsed)}s -> connection_lost")
            except Exception:
                pass
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

            # Lưu giữ trạng thái kết nối cho các luồng giao diện người dùng (UI).
            if self.window_manager:
                self.window_manager.set_shared_data("network_client", self.network_client)
                self.window_manager.set_shared_data("connected", True)

            self.is_connected = True
            self.last_pong_time = time.time()
            self.reconnect_attempts = 0  # Reset counter

            # Show success message
            self.toast_manager.success("Reconnected to server!")

            # Phát tín hiệu để khởi động lại các bộ hẹn giờ
            self.connection_restored.emit()

            # Hiển thị thông báo về việc đăng nhập lại
            self.toast_manager.warning("Please login again to continue")
            
        except Exception as e:
            self.toast_manager.error(f"Reconnect failed: {str(e)}")
            
            # Retry sau 2^n giây (exponential backoff)
            delay = min(2 ** self.reconnect_attempts, 30) * 1000
            QtCore.QTimer.singleShot(delay, self.attempt_reconnect)
            
    def return_to_welcome(self):
        """Quay về màn hình welcome"""
        self.stop()

        if self.window_manager:
            self.window_manager.set_shared_data("connected", False)
        
        self.window_manager.set_shared_data("user_id", None)
        self.window_manager.set_shared_data("username", None)
        self.window_manager.set_shared_data("current_room_id", None)
        
        # Navigate về welcome
        self.window_manager.navigate_to("welcome")