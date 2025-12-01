# 🖥️ Werewolf Game Server

C server với MySQL database xử lý game logic và player management.

---

## 📋 Yêu Cầu Hệ Thống

### Compiler & Build Tools
- **GCC** (GNU Compiler Collection)
- **Make** utility

### Libraries
- **MySQL C Connector** (`libmysqlclient-dev`)
- **OpenSSL** (`libssl-dev`) - Cho SHA256 password hashing

### Database
- **MySQL** hoặc **MariaDB** server

---

## 🚀 Cài Đặt

### Ubuntu/Debian

```bash
# Cài đặt dependencies
sudo apt-get update
sudo apt-get install gcc make libmysqlclient-dev libssl-dev mysql-server

# Khởi động MySQL
sudo service mysql start
```
---

## 🗄️ Setup Database

### 1. Khởi tạo Database

```bash
mysql -u root -p
```

```sql
CREATE DATABASE werewolf_game;
USE werewolf_game;

-- User table
CREATE TABLE user (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username)
);
```

### 2. Tạo file `.env`

Tạo file `.env` trong thư mục gốc project (không phải trong server/):

```env
DB_HOST=localhost
DB_USER=root
DB_PASS=your_password
DB_NAME=werewolf_game
DB_PORT=3306
```

**Lưu ý:** File `.env` phải ở cùng cấp với thư mục `server/` và `client/`

---

## 🔨 Build Server

```bash
cd server
make
```

Output: `werewolf_server` binary

### Makefile Targets

```bash
make          # Build server
make clean    # Xóa compiled files
make run      # Build và run server
make rebuild  # Clean + build
```

---

## 🚀 Chạy Server

```bash
cd server
./werewolf_server
```

Server sẽ chạy trên **port 5000**.

### Khi thành công:
```
Environment variables loaded from .env file.
Connected to database successfully.
SERVER RUNNING ON PORT 5000...
```

---

## 📁 Cấu Trúc Project

```
server/
├── Makefile                 # Build configuration
├── werewolf_server          # Compiled binary
│
├── include/                 # Các header files
│   ├──role_handlers/
│   │   ├──guard_handler.h  # Định nghĩa các hàm xử lý role bảo vệ
│   │   ├──seer_handler.h   # Định nghĩa các hàm xử lý role tiên tri
│   │   ├──villager_handler.h   # Định nghĩa các hàm xử lý role dân
│   │   └── werewolf_handler.h  # Định nghĩa các hàm xử lý role sói
│   ├── cJSON.h             # Thư viện json parsing
│   ├── protocol.h          # Định nghĩa packet headers
│   ├── types.h             # Định nghĩa các struct chung như Session, Player, Room,...
│   ├── database.h          # Các hàm liên quan đến database
│   ├── session_manager.h   # User sessions
│   ├── room_manager.h      # Quản lý phòng
│   └── packet_handler.h    # Xử lý từng packet cụ thể 
│
├── src/                     # Source files
│   ├──role_handlers/
│   │   ├──guard_handler.c 
│   │   ├──seer_handler.c  
│   │   ├──villager_handler.c   
│   │   └── werewolf_handler.c 
│   ├── main.c          # Khởi tạo chính
│   ├── server.c          
│   ├── cJSON.c           
│   ├── database.c         
│   ├── session_manager.c  
│   ├── room_manager.c     
│   └── packet_handler.c    
└── build/                   # Compiled object files (.o)
```

---
## 🛠️ Development
1. Define header trong `include/protocol.h`: (Nếu đã có protocol sẵn thì không cần bước này )
```c
#define MY_PACKET_REQ 999
#define MY_PACKET_RES 1000
```

2. Implement handler trong `src/packet_handler.c`:
```c
void handle_my_packet(int client_sock, cJSON *payload) {
    // Process request
    cJSON *response = cJSON_CreateObject();
    cJSON_AddStringToObject(response, "status", "success");
    
    // Send response
    send_packet(client_sock, MY_PACKET_RES, response);
    cJSON_Delete(response);
}
```

3. Add route trong `route_packet()`:
```c
switch (header) {
    case MY_PACKET_REQ:
        handle_my_packet(client_sock, payload);
        break;
}
```
---

**Happy Gaming! 🐺🌙**
