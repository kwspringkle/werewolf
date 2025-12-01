from PyQt5 import QtWidgets, QtCore


class WindowManager(QtCore.QObject):
    """Quản lý điều hướng và chuyển đổi giữa các cửa sổ"""
    
    # Signals
    window_changed = QtCore.pyqtSignal(str)  # window_name
    
    # Size và position mặc định
    DEFAULT_WIDTH = 800
    DEFAULT_HEIGHT = 700
    DEFAULT_X = None  # Sẽ được đặt khi hiển thị lần đầu
    DEFAULT_Y = None
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.windows = {}
        self.current_window = None
        self.shared_data = {}
        self.window_position_set = False
        
    def register_window(self, name, window_instance):
        """Đăng ký một cửa sổ"""
        self.windows[name] = window_instance
        
    def navigate_to(self, window_name, data=None):
        """Điều hướng đến một cửa sổ cụ thể"""
        if window_name not in self.windows:
            raise ValueError(f"Window '{window_name}' not registered")
            
        # Lưu vị trí của cửa sổ hiện tại trước khi ẩn
        if self.current_window:
            current = self.windows[self.current_window]
            if self.window_position_set:
                # Lưu vị trí hiện tại
                WindowManager.DEFAULT_X = current.x()
                WindowManager.DEFAULT_Y = current.y()
            current.hide()
            
        # Hiển thị cửa sổ mới
        new_window = self.windows[window_name]
        
        # Truyền data nếu có
        if data and hasattr(new_window, 'set_data'):
            new_window.set_data(data)
        
        # Set kích thước nhất quán
        new_window.resize(WindowManager.DEFAULT_WIDTH, WindowManager.DEFAULT_HEIGHT)
        
        # Set vị trí
        if WindowManager.DEFAULT_X is not None and WindowManager.DEFAULT_Y is not None:
            new_window.move(WindowManager.DEFAULT_X, WindowManager.DEFAULT_Y)
        elif not self.window_position_set:
            # Center window on first show
            screen = QtWidgets.QApplication.desktop().screenGeometry()
            x = (screen.width() - WindowManager.DEFAULT_WIDTH) // 2
            y = (screen.height() - WindowManager.DEFAULT_HEIGHT) // 2
            new_window.move(x, y)
            WindowManager.DEFAULT_X = x
            WindowManager.DEFAULT_Y = y
            self.window_position_set = True
        
        # Đảm bảo window flags cho phép nhận input
        new_window.setWindowFlags(QtCore.Qt.Window)
        
        # Hiển thị và focus window
        new_window.show()
        new_window.raise_()
        new_window.activateWindow()
        
        # Force set focus sau một delay nhỏ để đảm bảo window đã được hiển thị hoàn toàn
        QtCore.QTimer.singleShot(50, lambda: new_window.activateWindow())
        QtCore.QTimer.singleShot(100, lambda: new_window.setFocus())
        
        self.current_window = window_name
        self.window_changed.emit(window_name)
        
    def get_current_window(self):
        """Lấy instance cửa sổ hiện tại"""
        if self.current_window:
            return self.windows[self.current_window]
        return None
        
    def set_shared_data(self, key, value):
        """Lưu trữ dữ liệu chia sẻ giữa các cửa sổ"""
        self.shared_data[key] = value
        
    def get_shared_data(self, key, default=None):
        """Lấy dữ liệu chia sẻ"""
        return self.shared_data.get(key, default)
        
    def close_all(self):
        """Đóng tất cả các cửa sổ"""
        for window in self.windows.values():
            window.close()
