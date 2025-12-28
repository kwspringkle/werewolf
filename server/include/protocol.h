#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

// Định dạng gói tin
// [2 bytes header][4 bytes length][N bytes JSON payload]

typedef enum {
    // Authentication (100-199)
    LOGIN_REQ = 101,
    LOGIN_RES = 102,
    REGISTER_REQ = 103,
    REGISTER_RES = 104,
    LOGOUT_REQ = 105,
    LOGOUT_RES = 106,

    // Room management (200-299)
    GET_ROOMS_REQ = 201,
    GET_ROOMS_RES = 202,
    CREATE_ROOM_REQ = 203,
    CREATE_ROOM_RES = 204,
    JOIN_ROOM_REQ = 205,
    JOIN_ROOM_RES = 206,    
    ROOM_STATUS_UPDATE = 207,
    LEAVE_ROOM_REQ = 208,
    LEAVE_ROOM_RES = 209,
    GET_ROOM_INFO_REQ = 210,
    GET_ROOM_INFO_RES = 211,

    // Game flow (300-399)
    START_GAME_REQ = 301,
    GAME_START_RES_AND_ROLE = 302,
    PHASE_NIGHT = 303,
    PHASE_DAY = 304,
    GAME_OVER = 305,
    ROLE_CARD_DONE_REQ = 310,
    PHASE_GUARD_START = 311,  // Báo tất cả client chuyển sang guard phase
    PHASE_WOLF_START = 312,   // Báo tất cả client chuyển sang wolf phase

    // Game actions (400-499)
    CHAT_REQ = 401,
    CHAT_BROADCAST = 402,
    WOLF_KILL_REQ = 403,
    WOLF_KILL_RES = 404,
    SEER_CHECK_REQ = 405,
    SEER_RESULT = 406,
    GUARD_PROTECT_REQ = 407,
    GUARD_PROTECT_RES = 408,
    VOTE_REQ = 409,
    VOTE_STATUS_UPDATE = 410,
    VOTE_RESULT = 411,

    // System (500+)
    ERROR_MSG = 500,
    PING = 501,
    PONG = 502
} PacketType;

#endif // PROTOCOL_H