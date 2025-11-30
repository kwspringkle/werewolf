# 🐺 Werewolf Game - Ma Sói

Game Ma Sói trực tuyến nhiều người chơi với kiến trúc Client-Server.

**Server:** C + MySQL  
**Client:** Python + PyQt5 + C Socket Library  
**Platform:** WSL2 (Ubuntu)

---

## 📋 Tổng Quan

Dự án game ma sói với:
- Server viết bằng **C** xử lý logic game và database
- Client viết bằng **Python** với PyQt5 UI framework
- Socket communication qua **C library** (non-blocking)
- Real-time updates cho tất cả người chơi
- Modern UI với dark gothic theme
- Chạy hoàn toàn trên **WSL2**

---

## 🚀 Quick Start

### 1️⃣ Kiểm tra các gói đã cài

Hãy kiểm tra xem các gói cần thiết đã được cài chưa:

```bash
# Kiểm tra GCC (C compiler)
gcc --version
# Nếu chưa cài: command not found

# Kiểm tra Make
make --version

# Kiểm tra MySQL
mysql --version

# Kiểm tra Python3
python3 --version

# Kiểm tra pip3
pip3 --version

# Kiểm tra PyQt5
python3 -c "import PyQt5" 2>/dev/null && echo "PyQt5 đã cài" || echo "PyQt5 chưa cài"

# Kiểm tra MySQL dev library
dpkg -l | grep libmysqlclient-dev

# Kiểm tra OpenSSL dev library
dpkg -l | grep libssl-dev

# Kiểm tra font emoji
fc-list | grep -i emoji
```

### 2️⃣ Cài đặt Dependencies

**Cách 1: Cài từng gói (để debug nếu có lỗi)**

```bash
# Update package list
sudo apt update

# Build tools
sudo apt install -y gcc
sudo apt install -y make

# MySQL và libraries
sudo apt install -y mysql-server
sudo apt install -y libmysqlclient-dev
sudo apt install -y libssl-dev

# Python
sudo apt install -y python3
sudo apt install -y python3-pip
sudo apt install -y python3-pyqt5

# Font và X11 libraries (cho GUI)
sudo apt install -y fonts-noto-color-emoji
sudo apt install -y libxcb-xinerama0
sudo apt install -y libxcb-cursor0
```

**Cách 2: Cài tất cả một lần (khuyến nghị)**

```bash
sudo apt update && sudo apt install -y \
    gcc \
    make \
    libmysqlclient-dev \
    libssl-dev \
    mysql-server \
    python3 \
    python3-pip \
    python3-pyqt5 \
    fonts-noto-color-emoji \
    libxcb-xinerama0 \
    libxcb-cursor0
```

**Giải thích từng gói:**
- `gcc`: GNU C Compiler - biên dịch code C
- `make`: Build automation tool
- `mysql-server`: Database server
- `libmysqlclient-dev`: MySQL C library (cho server)
- `libssl-dev`: OpenSSL library (mã hóa password)
- `python3`: Python runtime (cho client)
- `python3-pip`: Python package manager
- `python3-pyqt5`: GUI framework
- `fonts-noto-color-emoji`: Font hỗ trợ emoji trong UI
- `libxcb-xinerama0, libxcb-cursor0`: X11 libraries cho GUI trên WSL

### 3️⃣ Xác nhận cài đặt thành công

```bash
# Kiểm tra lại tất cả
echo "=== GCC ===" && gcc --version | head -1
echo "=== Make ===" && make --version | head -1
echo "=== MySQL ===" && mysql --version
echo "=== Python3 ===" && python3 --version
echo "=== pip3 ===" && pip3 --version
echo "=== PyQt5 ===" && python3 -c "import PyQt5; print('PyQt5 OK')"
```

Nếu tất cả lệnh trên chạy không lỗi → Cài đặt thành công! ✅

### 4️⃣ Setup Database

```bash
# Khởi động MySQL
sudo service mysql start

# Kiểm tra MySQL đang chạy
sudo service mysql status

# Tạo database
mysql -u root -p
```

Trong MySQL shell:

```sql
CREATE DATABASE werewolf_game;
USE werewolf_game;

CREATE TABLE user (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username)
);

-- Kiểm tra table đã tạo
SHOW TABLES;
DESCRIBE user;

-- Thoát MySQL
EXIT;
```

### 5️⃣ Cấu hình môi trường

Tạo file `.env` ở thư mục gốc project:

```bash
# Trong thư mục werewolf/
nano .env
```

Cấu hình tương tự với file ```.env.example```

### 6️⃣ Build & Run

#### **Bước 1: Compile Server**
```bash
cd server
make

# Kiểm tra file binary đã được tạo
ls -lh werewolf_server
```

Nếu thấy file `werewolf_server` → Compile thành công! ✅

#### **Bước 2: Chạy Server**
```bash
./werewolf_server
```

Kết quả mong đợi:
```
Environment variables loaded from .env file.
Connected to database successfully.
SERVER RUNNING ON PORT 5000...
```

#### **Bước 3: Compile Client C Library**

Mở terminal mới (giữ server chạy):

```bash
cd client/lib
make

# Kiểm tra file .so đã được tạo
ls -lh *.so
```

#### **Bước 4: Setup X Server (cho GUI trên WSL)**

**Windows 11:** GUI đã được hỗ trợ tự động, bỏ qua bước này.

**Windows 10:** 
1. Cài **VcXsrv** hoặc **X410**
2. Chạy lệnh:
```bash
export DISPLAY=:0
```

#### **Bước 5: Chạy Client**
```bash
cd client
python3 main.py
```

Nếu GUI hiện lên → Thành công! 🎉

---

## 📁 Cấu Trúc Project

```
werewolf/
├── README.md                    
├── .env                         # Database config
├── .env.example                 # env example   
│
├── server/                      # C Server
│   ├── README.md               
│   ├── Makefile
│   ├── werewolf_server          # Binary sau compile
│   ├── include/                 # Header files
│   │   ├── database.h
│   │   ├── room_manager.h
│   │   └── ....  
│   └── src/                     # Source code
│       ├── main.c
│       └── ....
│
└── client/                      # Python Client
    ├── README.md         
    ├── main.py                  # Entry point
    ├── assets/
    │   ├── images/              # Logo
    │   │   └── werewolf_logo.png
    │   └── werewolf_theme.qss   # Stylesheet
    ├── lib/                     # C Socket Library
    │   ├── Makefile
    │   ├── werewolf_client.c
    │   └── werewolf_client.h
    └── src/
        ├── network_client.py    # Python wrapper cho C lib
        ├── components/          # UI Components
        │   ├── toast_notification.py
        │   ├── window_manager.py
        │   └── user_header.py
        └── windows/             # UI Screens
            ├── welcome_window.py
            ├── register_window.py
            ├── login_window.py
            ├── lobby_window.py
            └── room_window.py
```

---

## 🎮 Cách Chơi

### 1. Khởi động MySQL (mỗi lần restart WSL)
```bash
sudo service mysql start
```

### 2. Khởi động Server
```bash
cd server
./werewolf_server
```

### 3. Kết nối Client
1. Chạy `python3 main.py`
2. Nhập host: `127.0.0.1`, port: `5000`
3. Click **Connect**

### 4. Đăng ký/Đăng nhập
- **Register**: Tạo tài khoản mới
- **Login**: Đăng nhập với tài khoản có sẵn

### 5. Tạo/Vào phòng
- **Create Room**: Tạo phòng mới (bạn là Host)
- **Join**: Vào phòng có sẵn

### 6. Bắt đầu game
- Cần tối thiểu **6 người chơi**
- Host click **Start Game**

---

## 📡 Network Protocol

### Packet Format
```
[Header: 2 bytes][Length: 4 bytes][Payload: JSON]
```

### Packet Types

| Code | Name | Description |
|------|------|-------------|
| **1xx** | **Authentication** | |
| 101 | LOGIN_REQ | Đăng nhập |
| 102 | LOGIN_RES | Kết quả đăng nhập |
| 103 | REGISTER_REQ | Đăng ký tài khoản |
| 104 | REGISTER_RES | Kết quả đăng ký |
| 105 | LOGOUT_REQ | Đăng xuất |
| **2xx** | **Room Management** | |
| 201 | GET_ROOMS_REQ | Lấy danh sách phòng |
| 202 | GET_ROOMS_RES | Trả danh sách phòng |
| 203 | CREATE_ROOM_REQ | Tạo phòng mới |
| 204 | CREATE_ROOM_RES | Kết quả tạo phòng |
| 205 | JOIN_ROOM_REQ | Vào phòng |
| 206 | JOIN_ROOM_RES | Kết quả vào phòng |
| 207 | ROOM_STATUS_UPDATE | Update real-time |
| 208 | LEAVE_ROOM_REQ | Rời phòng |
| 209 | LEAVE_ROOM_RES | Kết quả rời phòng |
| **3xx** | **Game Control** | |
| 301 | START_GAME_REQ | Bắt đầu game |
| 302 |GAME_START_RES_AND_ROLE | Phân vai |

---

## ✨ Tính Năng

### ✅ Đã Hoàn Thành
- [x] Đăng ký/Đăng nhập
- [x] Tạo và quản lý phòng chơi
- [x] Vào/rời phòng
- [x] Danh sách phòng real-time (auto-refresh)
- [x] Update người chơi trong phòng real-time
- [x] Toast notifications
- [x] Phân vai cho người chơi

### 🚧 Đang Phát Triển
- [⏳] Gameplay chính cho từng role
- [⏳] Chat 
- [⏳] Vote system

---

## 🛠️ Development

### Test nhiều client
```bash
# Terminal 1
python3 main.py

# Terminal 2
python3 main.py

# Terminal 3
python3 main.py
```

### Rebuild toàn bộ
```bash
# Server
cd server
make clean
make

# Client C library
cd client/lib
make clean
make
```

---

## 🐛 Troubleshooting

### Lỗi: `gcc: command not found`
```bash
sudo apt install gcc
```

### Lỗi: `mysql.h: No such file or directory`
```bash
sudo apt install libmysqlclient-dev
```

### Lỗi: `ModuleNotFoundError: No module named 'PyQt5'`
```bash
sudo apt install python3-pyqt5
# Hoặc
pip3 install PyQt5
```

### MySQL không chạy
```bash
sudo service mysql start
sudo service mysql status
```

### Lỗi: `ERROR 1045 (28000): Access denied`
```bash
# Reset MySQL root password
sudo mysql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'new_password';
FLUSH PRIVILEGES;
EXIT;
```

### Port 5000 bị chiếm
```bash
# Tìm process
lsof -i :5000

# Kill process
kill -9 <PID>
```

### Font emoji không hiển thị
```bash
sudo apt install fonts-noto-color-emoji
fc-cache -fv
```

### Client C library lỗi
```bash
cd client/lib
make clean
make

# Kiểm tra file .so
ls -la *.so

# Nếu không có file .so, kiểm tra lỗi compile
cat Makefile
```
---

## 📚 Documentation

Chi tiết xem:
- [Server README](server/README.md) - C server documentation
- [Client README](client/README.md) - Python client documentation

## 👥 Credit

**Nhóm 17**
- Đinh Ngọc Khánh Huyền
- Trần Khánh Quỳnh
