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