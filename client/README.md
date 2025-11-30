# 🎮 Werewolf Game Client

Python client với PyQt5 GUI và C socket library, chạy trên WSL2.

---

## 📋 Yêu Cầu Hệ Thống

### Python & Dependencies
- Python 3.8+
- PyQt5 (GUI framework)
- ctypes (Python wrapper cho C library - built-in)

### C Compiler
- GCC (để build socket library)

---

## 🚀 Cài Đặt

### 1. Kiểm tra Python và PyQt5

```bash
# Kiểm tra Python
python3 --version

# Kiểm tra PyQt5
python3 -c "import PyQt5" 2>/dev/null && echo "✅ PyQt5 đã cài" || echo "❌ PyQt5 chưa cài"
```

### 2. Cài đặt Dependencies

```bash
pip3 install PyQt5
```

### 3. Compile C Socket Library

```bash
cd lib
make

# Kiểm tra file .so đã được tạo
ls -lh *.so
```

Nếu thấy file `werewolf_client.so` → Compile thành công! ✅

### 4. Setup X Server (cho GUI trên WSL)

**Windows 11:** GUI đã được hỗ trợ tự động, bỏ qua bước này.

**Windows 10:**
```bash
# Cài VcXsrv hoặc X410 trên Windows, sau đó:
export DISPLAY=:0

# Thêm vào ~/.bashrc để tự động:
echo 'export DISPLAY=:0' >> ~/.bashrc
source ~/.bashrc
```

---

## 🎯 Chạy Client

```bash
cd client
python3 main.py
```

**Lưu ý:** Server phải đang chạy trước khi connect!

---

## 📁 Cấu Trúc Project

```
client/
├── main.py                      # Điểm vào ứng dụng - WerewolfApplication
│
├── assets/
│   ├── werewolf_theme.qss      # Stylesheet (giao diện tối, phong cách gothic)
│   └── images/                 # Thư mục chứa ảnh/icon game
│       └── werewolf_logo.png
│
├── lib/                         # Thư viện C Socket
│   ├── Makefile                # Script build
│   ├── werewolf_client.h       # Header file
│   ├── werewolf_client.c       # Cài đặt Socket
│   └── werewolf_client.so      # Thư viện đã biên dịch (sau khi make)
│
└── src/
    ├── network_client.py        # Wrapper Python cho thư viện C
    │
    ├── components/              # Các thành phần UI tái sử dụng
    │   ├── __init__.py
    │   ├── toast_notification.py   # Hệ thống thông báo kiểu toast
    │   ├── window_manager.py       # Quản lý điều hướng cửa sổ
    │   └── user_header.py          # Header người dùng với chức năng đăng xuất
    │
    ├── utils/                   # Các hàm tiện ích
    │   ├── __init__.py
    │   └── image_utils.py       # Hàm hỗ trợ load ảnh
    │
    └── windows/                 # Các màn hình giao diện
        ├── __init__.py
        ├── welcome_window.py    # Màn hình kết nối
        ├── register_window.py   # Màn hình đăng ký
        ├── login_window.py      # Màn hình đăng nhập
        ├── lobby_window.py      # Màn hình danh sách phòng
        ├── role_card_window.py  # Hiển thị vai trò người chơi
        └── room_window.py       # Màn hình bên trong phòng

```

---

## 🔧 Development

### Thêm Window Mới

**Bước 1:** Tạo file trong `src/windows/`

```python
# my_window.py
from PyQt5 import QtWidgets, QtCore

class MyWindow(QtWidgets.QWidget):
    def __init__(self, toast_manager, window_manager, network_client):
        super().__init__()
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.network_client = network_client
        self.setup_ui()
        
    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("My Window")
        layout.addWidget(label)
        self.setLayout(layout)
```

**Bước 2:** Register trong `main.py`

```python
from src.windows.my_window import MyWindow

class WerewolfApplication:
    def __init__(self):
        # ... existing code ...
        
        # Thêm window mới
        self.my_window = MyWindow(
            self.toast_manager,
            self.window_manager,
            self.network_client
        )
        self.window_manager.register_window("my_window", self.my_window)
```

**Bước 3:** Navigate từ window khác

```python
# Trong button handler
def on_button_click(self):
    self.window_manager.navigate_to("my_window")
```

### Xử lý Packet trong Window

```python
class MyWindow(QtWidgets.QWidget):
    def __init__(self, ...):
        super().__init__()
        # Setup timer để check packets
        self.packet_timer = QtCore.QTimer()
        self.packet_timer.timeout.connect(self.check_packets)
        self.packet_timer.start(100)  # Check mỗi 100ms
        
    def check_packets(self):
        header, payload = self.network_client.receive_packet()
        if header > 0:
            self.handle_packet(header, payload)
            
    def handle_packet(self, header, payload):
        if header == 999:  # MY_PACKET (Phải được định nghĩa trong include/protocol.h)
            self.toast_manager.info(payload["message"])
            # Update UI
```

---

## 🐛 Troubleshooting

### Lỗi: `ModuleNotFoundError: No module named 'PyQt5'`
```bash
sudo apt install python3-pyqt5
# Hoặc
pip3 install PyQt5
```

### Lỗi: `OSError: werewolf_client.so: cannot open shared object file`
```bash
# Compile lại C library
cd lib
make clean
make

# Kiểm tra file .so
ls -la *.so
```

### GUI không hiển thị trên WSL
```bash
# Windows 10: Setup X server
export DISPLAY=:0

# Windows 11: Đảm bảo WSLg đang chạy
# Nếu không work, thử:
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
```

### Client crash khi send/receive packet
```bash
# Kiểm tra server có đang chạy không
# Kiểm tra kết nối trong Welcome window
# Check console output cho error messages
```
---

## 📊 Data Flow

```
User Action
    ↓
Window Event Handler
    ↓
NetworkClient.send_packet()
    ↓
C Library (werewolf_client.so)
    ↓
Server
    ↓
C Library receives response
    ↓
NetworkClient.receive_packet()
    ↓
Window.handle_packet()
    ↓
ToastManager (notification) + UI Update
    ↓
WindowManager.navigate_to() (nếu cần)
```

---
**Happy Gaming! 🐺🌙**