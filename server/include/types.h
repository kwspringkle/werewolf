#ifndef TYPES_H
#define TYPES_H

#include <time.h>
#include "cJSON.h" 

typedef struct Session Session;
typedef struct Player Player;
typedef struct Room Room;

#define PORT 5000
#define MAX_ROOMS 10
#define MAX_PLAYERS_PER_ROOM 12
#define MIN_PLAYERS_TO_START 6
#define MAX_SESSIONS 30

// Session structure
struct Session {
    int socket;
    int user_id;
    char username[50];
    int is_logged_in;
    time_t last_ping;
};

// Cấu trúc struct Player
struct Player {
    int socket;
    int user_id;
    char username[50];
    int role;
    int is_alive;
};

// Cấu trúc phòng
struct Room {
    int id;
    char name[50];
    Player players[12];  // MAX_PLAYERS_PER_ROOM
    int current_players;
    int status;          // RoomStatus enum
    int host_socket;
    /* Night-phase state */
    int night_phase_active;      // 1 if night actions are being collected
    time_t seer_deadline;        // deadline for seer to act (epoch seconds)
    time_t guard_deadline;       // deadline for guard to act (epoch seconds)
    time_t wolf_deadline;        // deadline for wolf to act (epoch seconds)
    int seer_choice_made;        // 1 if seer has already chosen this night
    char seer_chosen_target[50]; // username chosen by seer
    int guard_choice_made;       // 1 if guard has already chosen this night
    char guard_protected_username[50]; // username được bảo vệ bởi guard
    char wolf_votes[MAX_PLAYERS_PER_ROOM][50]; // username bị mỗi sói chọn ("" nếu chưa vote)
    int wolf_vote_count; // số lượng sói đã vote đêm nay
    int wolf_kill_done; // 1 nếu đã tổng hợp và xử lý kill đêm nay
    /* Role card reading phase */
    int role_card_done_count; // số người đã đọc xong role card
    int role_card_total; // tổng số người chơi
    time_t role_card_start_time; // thời gian bắt đầu đọc role card (để timeout sau 30s)
};

// Room status enum
typedef enum {
    ROOM_WAITING = 0,
    ROOM_PLAYING = 1,
    ROOM_FINISHED = 2
} RoomStatus;

// Định nghĩa player role
typedef enum {
    ROLE_VILLAGER = 0,
    ROLE_WEREWOLF = 1,
    ROLE_SEER = 2,
    ROLE_GUARD = 3
} PlayerRole;

extern Room rooms[MAX_ROOMS];
extern Session sessions[MAX_SESSIONS];
extern int session_count;
#endif // TYPES_H