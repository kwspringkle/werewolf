# Tài liệu Payload Mẫu cho Các Gói Tin

## Định dạng gói tin
```
[2 bytes header][4 bytes length][N bytes JSON payload]
```

Header và length được encode theo big-endian. Payload là JSON string.

---

## Nhóm Authentication (100-199)

### 101: LOGIN_REQ - Yêu cầu đăng nhập
**Client → Server**

```json
{
  "username": "player1",
  "password": "mypassword123"
}
```

### 102: LOGIN_RES - Phản hồi đăng nhập
**Server → Client**

**Thành công:**
```json
{
  "status": "success",
  "user_id": 1,
  "username": "player1",
  "resume_room_id": 5,
  "resume_room_status": 1,
  "resume_as_spectator": 0
}
```

**Thất bại:**
```json
{
  "status": "fail",
  "message": "Wrong username or password"
}
```

**Lỗi:**
```json
{
  "status": "error",
  "message": "Database error"
}
```

### 103: REGISTER_REQ - Yêu cầu đăng ký
**Client → Server**

```json
{
  "username": "newuser",
  "password": "securepass123"
}
```

### 104: REGISTER_RES - Phản hồi đăng ký
**Server → Client**

**Thành công:**
```json
{
  "status": "success"
}
```

**Thất bại:**
```json
{
  "status": "fail",
  "message": "Username already exists"
}
```

**Lỗi:**
```json
{
  "status": "error",
  "message": "Server error"
}
```

### 105: LOGOUT_REQ - Yêu cầu đăng xuất
**Client → Server**

```json
{}
```

### 106: LOGOUT_RES - Phản hồi đăng xuất
**Server → Client**

```json
{
  "status": "success",
  "message": "Logged out successfully"
}
```

---

## Nhóm Room Management (200-299)

### 201: GET_ROOMS_REQ - Yêu cầu lấy danh sách phòng
**Client → Server**

```json
{}
```

### 202: GET_ROOMS_RES - Phản hồi danh sách phòng
**Server → Client**

```json
[
  {
    "id": 1,
    "name": "Room 1",
    "current": 3,
    "max": 12,
    "status": 0
  },
  {
    "id": 2,
    "name": "Room 2",
    "current": 6,
    "max": 12,
    "status": 1
  }
]
```

**Lưu ý:** `status`: 0 = ROOM_WAITING, 1 = ROOM_PLAYING

### 203: CREATE_ROOM_REQ - Yêu cầu tạo phòng
**Client → Server**

```json
{
  "room_name": "My Game Room"
}
```

### 204: CREATE_ROOM_RES - Phản hồi tạo phòng
**Server → Client**

**Thành công:**
```json
{
  "status": "success",
  "room_id": 5,
  "room_name": "My Game Room"
}
```

**Thất bại:**
```json
{
  "status": "fail",
  "message": "Room name already exists"
}
```

### 205: JOIN_ROOM_REQ - Yêu cầu tham gia phòng
**Client → Server**

```json
{
  "room_id": 5
}
```

### 206: JOIN_ROOM_RES - Phản hồi tham gia phòng
**Server → Client**

**Thành công:**
```json
{
  "status": "success",
  "is_host": 0,
  "room_id": 5,
  "room_name": "My Game Room",
  "players": [
    {"username": "player1"},
    {"username": "player2"},
    {"username": "player3"}
  ]
}
```

**Thất bại:**
```json
{
  "status": "fail",
  "message": "Room is full"
}
```

### 207: ROOM_STATUS_UPDATE - Cập nhật trạng thái phòng
**Server → Client (Broadcast)**

**Player joined:**
```json
{
  "type": "player_joined",
  "username": "newplayer",
  "current_players": 4
}
```

**Player left:**
```json
{
  "type": "player_left",
  "username": "leavingplayer",
  "current_players": 3,
  "new_host": "player1"
}
```

**Player disconnected (game not started):**
```json
{
  "type": "player_disconnected",
  "username": "disconnectedplayer",
  "current_players": 2,
  "game_started": false,
  "new_host": "player1"
}
```

**Player disconnected (game started):**
```json
{
  "type": "player_disconnected",
  "username": "disconnectedplayer",
  "message": "Player disconnected",
  "game_started": true
}
```

### 208: LEAVE_ROOM_REQ - Yêu cầu rời phòng
**Client → Server**

```json
{}
```

### 209: LEAVE_ROOM_RES - Phản hồi rời phòng
**Server → Client**

**Thành công:**
```json
{
  "status": "success",
  "message": "Left room successfully"
}
```

**Thất bại:**
```json
{
  "status": "fail",
  "message": "You are not in any room"
}
```

### 210: GET_ROOM_INFO_REQ - Yêu cầu thông tin phòng
**Client → Server**

```json
{
  "room_id": 5
}
```

### 211: GET_ROOM_INFO_RES - Phản hồi thông tin phòng
**Server → Client**

**Thành công:**
```json
{
  "status": "success",
  "room_id": 5,
  "room_name": "My Game Room",
  "current_players": 6,
  "max_players": 12,
  "room_status": 1,
  "day_phase_active": 0,
  "day_round": 0,
  "day_deadline": 0,
  "night_phase_active": 0,
  "role_card_done_count": 0,
  "role_card_total": 0,
  "role_card_start_time": 0,
  "seer_deadline": 0,
  "guard_deadline": 0,
  "wolf_deadline": 0,
  "players": [
    {
      "username": "player1",
      "user_id": 1,
      "is_host": 1,
      "is_alive": 1
    },
    {
      "username": "player2",
      "user_id": 2,
      "is_host": 0,
      "is_alive": 1
    }
  ]
}
```

**Khi đang ở day phase round 2:**
```json
{
  "status": "success",
  "room_id": 5,
  "room_name": "My Game Room",
  "current_players": 6,
  "max_players": 12,
  "room_status": 1,
  "day_phase_active": 1,
  "day_round": 2,
  "day_deadline": 1703123456.0,
  "day_candidates": ["player1", "player2"],
  "players": [...]
}
```

---

## Nhóm Game Flow (300-399)

### 301: START_GAME_REQ - Yêu cầu bắt đầu game
**Client → Server**

```json
{
  "room_id": 5
}
```

**Lưu ý:** Chỉ host mới có thể gửi request này.

### 302: GAME_START_RES_AND_ROLE - Phản hồi bắt đầu game kèm vai trò
**Server → Client**

**Vai trò Werewolf:**
```json
{
  "status": "success",
  "message": "Game started",
  "role": 1,
  "role_name": "Werewolf",
  "role_icon": "🐺",
  "role_description": "You are a WEREWOLF! You know other werewolves. At night, discuss with your team to kill one villager. Your goal: Eliminate all villagers.",
  "werewolf_team": ["player2", "player5"]
}
```

**Vai trò Seer:**
```json
{
  "status": "success",
  "message": "Game started",
  "role": 2,
  "role_name": "Seer",
  "role_icon": "🔮",
  "role_description": "You are the SEER! Each night, you can check one player to know if they are a werewolf or not. Use your knowledge wisely to guide the village."
}
```

**Vai trò Guard:**
```json
{
  "status": "success",
  "message": "Game started",
  "role": 3,
  "role_name": "Guard",
  "role_icon": "🛡️",
  "role_description": "You are the GUARD! Each night, you can protect one player from werewolf attacks. Choose wisely to save the village."
}
```

**Vai trò Villager:**
```json
{
  "status": "success",
  "message": "Game started",
  "role": 0,
  "role_name": "Villager",
  "role_icon": "👤",
  "role_description": "You are a VILLAGER! You have no special powers, but you can vote during the day to eliminate suspected werewolves. Work with others to find the werewolves!"
}
```

**Lưu ý:** `role`: 0 = VILLAGER, 1 = WEREWOLF, 2 = SEER, 3 = GUARD

### 303: PHASE_NIGHT - Chuyển sang giai đoạn đêm
**Server → Client (Broadcast)**

```json
{
  "type": "phase_night",
  "duration": 180,
  "seer_duration": 60,
  "guard_duration": 60,
  "wolf_duration": 60,
  "seer_deadline": 1703123456.0,
  "guard_deadline": 1703123516.0,
  "wolf_deadline": 1703123576.0,
  "players": [
    {
      "username": "player1",
      "is_alive": 1
    },
    {
      "username": "player2",
      "is_alive": 1
    }
  ]
}
```

**Lưu ý:** Các deadline là epoch seconds (số thực).

### 304: PHASE_DAY - Chuyển sang giai đoạn ngày
**Server → Client (Broadcast)**

```json
{
  "type": "phase_day",
  "result": "killed",
  "targetId": "player3",
  "day_duration": 300,
  "day_deadline": 1703123756.0
}
```

**Không có ai chết:**
```json
{
  "type": "phase_day",
  "result": "no_kill",
  "day_duration": 300,
  "day_deadline": 1703123756.0
}
```

### 305: GAME_OVER - Kết thúc game
**Server → Client (Broadcast)**

```json
{
  "type": "game_over",
  "winner": "villagers",
  "players": [
    {
      "username": "player1",
      "role": 0,
      "is_alive": 1
    },
    {
      "username": "player2",
      "role": 1,
      "is_alive": 0
    }
  ]
}
```

**Lưu ý:** `winner` có thể là `"villagers"` hoặc `"werewolves"`.

### 310: ROLE_CARD_DONE_REQ - Xác nhận đã xem vai
**Client → Server**

```json
{
  "room_id": 5
}
```

### 311: PHASE_GUARD_START - Chuyển sang phase Bảo vệ
**Server → Client (Broadcast)**

```json
{
  "type": "phase_guard_start",
  "guard_duration": 60,
  "guard_deadline": 1703123516.0,
  "wolf_deadline": 1703123576.0
}
```

### 312: PHASE_WOLF_START - Chuyển sang phase Sói
**Server → Client (Broadcast)**

```json
{
  "type": "phase_wolf_start",
  "wolf_duration": 60,
  "wolf_deadline": 1703123576.0
}
```

---

## Nhóm Game Actions (400-499)

### 401: CHAT_REQ - Yêu cầu gửi chat
**Client → Server**

```json
{
  "room_id": 5,
  "message": "Hello everyone!"
}
```

**Lưu ý:** 
- Message tối đa 500 ký tự
- Trong đêm, chỉ werewolf có thể chat (wolf chat)
- Trong ngày, tất cả người chơi còn sống có thể chat (day chat)
- Người chết không thể chat

### 402: CHAT_BROADCAST - Broadcast tin nhắn chat
**Server → Client (Broadcast)**

**Day chat:**
```json
{
  "username": "player1",
  "message": "Hello everyone!",
  "room_id": 5,
  "chat_type": "day"
}
```

**Wolf chat (chỉ gửi cho werewolf còn sống):**
```json
{
  "username": "player2",
  "message": "Let's kill player1",
  "room_id": 5,
  "chat_type": "wolf"
}
```

### 403: WOLF_KILL_REQ - Sói yêu cầu giết người
**Client → Server**

```json
{
  "room_id": 5,
  "target_username": "player3"
}
```

**Skip (không chọn ai):**
```json
{
  "room_id": 5,
  "target_username": ""
}
```

### 404: WOLF_KILL_RES - Phản hồi hành động giết
**Server → Client**

**Vote thành công:**
```json
{
  "type": "wolf_vote_received"
}
```

**Skip:**
```json
{
  "type": "wolf_vote_received",
  "skipped": true
}
```

### 405: SEER_CHECK_REQ - Tiên tri yêu cầu kiểm tra
**Client → Server**

```json
{
  "room_id": 5,
  "target_username": "player3"
}
```

**Skip (không kiểm tra ai):**
```json
{
  "room_id": 5,
  "target_username": ""
}
```

### 406: SEER_RESULT - Kết quả kiểm tra của Tiên tri
**Server → Client**

**Kiểm tra thành công:**
```json
{
  "status": "success",
  "target_username": "player3",
  "is_werewolf": true,
  "players": [
    {
      "username": "player1",
      "is_alive": true
    },
    {
      "username": "player2",
      "is_alive": true
    },
    {
      "username": "player3",
      "is_alive": true
    }
  ]
}
```

**Skip:**
```json
{
  "status": "success",
  "skipped": true,
  "players": [...]
}
```

**Thất bại:**
```json
{
  "status": "fail",
  "message": "Seer has already made a choice this night",
  "players": [...]
}
```

### 407: GUARD_PROTECT_REQ - Bảo vệ yêu cầu bảo vệ
**Client → Server**

```json
{
  "room_id": 5,
  "target_username": "player3"
}
```

**Skip (không bảo vệ ai):**
```json
{
  "room_id": 5,
  "target_username": ""
}
```

### 408: GUARD_PROTECT_RES - Phản hồi hành động bảo vệ
**Server → Client**

**Bảo vệ thành công:**
```json
{
  "status": "success",
  "target_username": "player3",
  "players": [
    {
      "username": "player1",
      "is_alive": true
    },
    {
      "username": "player2",
      "is_alive": true
    },
    {
      "username": "player3",
      "is_alive": true
    }
  ]
}
```

**Skip:**
```json
{
  "status": "success",
  "skipped": true,
  "players": [...]
}
```

**Thất bại:**
```json
{
  "status": "fail",
  "message": "Guard has already made a choice this night",
  "players": [...]
}
```

### 409: VOTE_REQ - Yêu cầu bỏ phiếu
**Client → Server**

```json
{
  "room_id": 5,
  "target_username": "player3"
}
```

**Skip (không vote ai):**
```json
{
  "room_id": 5,
  "target_username": ""
}
```

**Lưu ý:** 
- Chỉ người chơi còn sống mới có thể vote
- Round 2 chỉ có thể vote cho các candidate được chỉ định

### 410: VOTE_STATUS_UPDATE - Cập nhật trạng thái vote
**Server → Client (Broadcast)**

```json
{
  "type": "vote_status",
  "voted_count": 4,
  "total_alive": 6,
  "remaining_time": 120
}
```

### 411: VOTE_RESULT - Kết quả bỏ phiếu
**Server → Client (Broadcast)**

**Round 1 - Có người bị vote nhiều nhất (không hòa):**
```json
{
  "type": "execution",
  "target": "player3",
  "votes": 4
}
```

**Round 1 - Hòa, chuyển sang Round 2:**
```json
{
  "type": "tie_break_start",
  "candidates": ["player1", "player2"],
  "timer": 60,
  "deadline": 1703123756.0
}
```

**Round 2 - Hòa, random chọn:**
```json
{
  "type": "execution_random_selected",
  "candidates": ["player1", "player2"],
  "selected": "player1",
  "reason": "tie_break_still_equal"
}
```

**Không có ai bị vote (chuyển sang đêm):**
```json
{
  "type": "no_execution",
  "message": "No one was voted out"
}
```

---

## Nhóm System (500+)

### 500: ERROR_MSG - Thông báo lỗi
**Server → Client**

```json
{
  "status": "fail",
  "message": "Invalid or missing room_id/message"
}
```

**Lỗi vote:**
```json
{
  "type": "vote_error",
  "message": "Dead players cannot vote"
}
```

### 501: PING - Gói tin kiểm tra kết nối
**Server → Client** hoặc **Client → Server**

```json
{
  "type": "ping"
}
```

### 502: PONG - Phản hồi kiểm tra kết nối
**Server → Client** hoặc **Client → Server**

```json
{
  "type": "pong"
}
```

---

## Ghi chú

1. **Deadline format:** Tất cả các deadline được gửi dưới dạng epoch seconds (số thực, ví dụ: `1703123456.0`)

2. **Empty payload:** Một số request không cần payload, có thể gửi `{}` hoặc empty object

3. **Broadcast packets:** Các packet được đánh dấu "(Broadcast)" sẽ được gửi đến tất cả người chơi trong phòng

4. **Role values:**
   - `0` = VILLAGER
   - `1` = WEREWOLF
   - `2` = SEER
   - `3` = GUARD

5. **Room status:**
   - `0` = ROOM_WAITING
   - `1` = ROOM_PLAYING

6. **Chat types:**
   - `"day"` = Chat ban ngày (tất cả người chơi)
   - `"wolf"` = Chat sói (chỉ werewolf trong đêm)

