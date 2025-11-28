# Werewolf Game - Ma Sói

Game Ma Sói nhiều người chơi với kiến trúc Client-Server.

## Yêu cầu hệ thống

### Server (C)
- GCC compiler
- MySQL/MariaDB
- Thư viện MySQL C connector
- cJSON library

### Client (Python)
- Python 3.x
- PyQt5

## Cài đặt

### 1. Cài đặt dependencies

**Ubuntu/Linux:**
```bash
# Server dependencies
sudo apt-get install gcc make libmysqlclient-dev mysql-server

# Client dependencies
pip3 install PyQt5
```

**Windows:**
- Cài đặt MinGW/GCC
- Cài đặt MySQL
- Cài đặt Python 3.x
- `pip install PyQt5`

### 2. Cấu hình Database

Tạo database và bảng:

```sql
CREATE DATABASE werewolf_game;
USE werewolf_game;

CREATE TABLE user (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Cấu hình môi trường

Tạo file `.env` trong thư mục gốc:

```
DB_HOST=localhost
DB_USER=root
DB_PASS=your_password
DB_NAME=werewolf_game
DB_PORT=3306
```

## Chạy ứng dụng

### Bước 1: Compile và chạy Server

```bash
cd server
make
./build/werewolf_server
```

Server sẽ chạy trên port **5000**.

Khi thành công, bạn sẽ thấy:
```
Environment variables loaded from .env file.
Connected to database successfully.
SERVER RUNNING ON PORT 5000...
```

### Bước 2: Chạy Client

Mở terminal mới (giữ server chạy):

```bash
cd client/src
python3 client_room.py
```

## Cách sử dụng Client

### 1. Kết nối
- Host: `127.0.0.1`
- Port: `5000`
- Click **Connect**

### 2. Đăng nhập
- **Login**: Đăng nhập với tài khoản có sẵn
- **Register**: Đăng ký tài khoản mới (ở client_login.py)

Sau khi login thành công:
- Danh sách phòng tự động hiển thị
- Auto-refresh mỗi 3 giây

### 3. Quản lý phòng

**Tạo phòng mới:**
1. Nhập tên phòng
2. Click **Create Room**
3. Bạn sẽ là Host của phòng

**Vào phòng:**
1. Tìm phòng trong danh sách (trạng thái WAITING)
2. Click nút **Join**

**Rời phòng:**
- Click **Leave Room**

### 4. Bắt đầu game (chỉ Host)

- Cần tối thiểu **6 người chơi**
- Host click **Start Game**

## Cấu trúc dự án

```
werewolf/
├── server/
│   ├── src/
│   │   ├── server.c      # Code server chính
│   │   └── cJSON.c/h     # Thư viện JSON
│   ├── build/            # File build output
│   └── Makefile
├── client/
│   └── src/
│       ├── client_login.py  # Client đăng nhập cơ bản
│       └── client_room.py   # Client quản lý phòng (đầy đủ)
└── .env                  # Cấu hình database
```

## Protocol Communication

### Packet Header Format
```
[Header: 2 bytes][Length: 4 bytes][Payload: JSON]
```

### Packet Headers

**Authentication (1xx):**
- `101` - LOGIN_REQ
- `102` - LOGIN_RES
- `103` - REGISTER_REQ
- `104` - REGISTER_RES

**Room Management (2xx):**
- `201` - GET_ROOMS_REQ
- `202` - GET_ROOMS_RES
- `203` - CREATE_ROOM_REQ
- `204` - CREATE_ROOM_RES
- `205` - JOIN_ROOM_REQ
- `206` - JOIN_ROOM_RES
- `207` - ROOM_STATUS_UPDATE
- `208` - LEAVE_ROOM_REQ
- `209` - LEAVE_ROOM_RES

**Game Control (3xx):**
- `301` - START_GAME_REQ
- `302` - GAME_START_RES_AND_ROLE

**In-game Actions (4xx):**
- `401` - CHAT_REQ
- `407` - VOTE_REQ
- (Chưa implement)

## Tính năng hiện tại

✅ Đăng ký/Đăng nhập
✅ Tạo phòng
✅ Vào/rời phòng
✅ Xem danh sách phòng (auto-refresh)
✅ Real-time cập nhật người chơi trong phòng
✅ Start game (Host only)
⏳ Phân vai
⏳ Gameplay chính
⏳ Chat
⏳ Vote

## Debug

### Server không kết nối được database
- Kiểm tra file `.env`
- Kiểm tra MySQL service đang chạy: `sudo service mysql status`
- Kiểm tra quyền user database

### Client không kết nối được server
- Kiểm tra server đang chạy
- Kiểm tra port 5000 không bị chiếm: `netstat -an | grep 5000`
- Kiểm tra firewall

### Build error
```bash
# Clean và build lại
cd server
make clean
make
```

## Test nhiều người chơi

Mở nhiều terminal và chạy client:

```bash
# Terminal 1
python3 client_room.py

# Terminal 2
python3 client_room.py

# Terminal 3
python3 client_room.py
```

Hoặc chạy background (Linux/Mac):
```bash
python3 client_room.py &
python3 client_room.py &
python3 client_room.py &
```

## Quick Start

```bash
# 1. Setup database
mysql -u root -p < setup.sql

# 2. Tạo .env file
echo "DB_HOST=localhost
DB_USER=root
DB_PASS=yourpassword
DB_NAME=werewolf_game
DB_PORT=3306" > .env

# 3. Compile server
cd server && make

# 4. Chạy server
./build/werewolf_server

# 5. Mở terminal mới, chạy client
cd client/src
python3 client_room.py
```

## Tác giả

THLTM Team - 2025
