#include <string.h>
#include <stdio.h>
#include "packet_handler.h"
#include "protocol.h"
#include "cJSON.h"
#include "types.h"
#include "room_manager.h"
#include "session_manager.h"

extern Room rooms[MAX_ROOMS];

void handle_chat_message(int client_fd, cJSON *json) {
    // Get room_id and message from request
    cJSON *room_id_obj = cJSON_GetObjectItemCaseSensitive(json, "room_id");
    cJSON *message_obj = cJSON_GetObjectItemCaseSensitive(json, "message");

    if (!room_id_obj || !cJSON_IsNumber(room_id_obj) ||
        !message_obj || !cJSON_IsString(message_obj)) {
        cJSON *error = cJSON_CreateObject();
        cJSON_AddStringToObject(error, "status", "fail");
        cJSON_AddStringToObject(error, "message", "Invalid or missing room_id/message");
        char *error_str = cJSON_PrintUnformatted(error);
        send_packet(client_fd, ERROR_MSG, error_str);
        free(error_str);
        cJSON_Delete(error);
        return;
    }

    int room_id = room_id_obj->valueint;
    const char *message = message_obj->valuestring;

    // Validate message length
    if (strlen(message) == 0 || strlen(message) > 500) {
        cJSON *error = cJSON_CreateObject();
        cJSON_AddStringToObject(error, "status", "fail");
        cJSON_AddStringToObject(error, "message", "Message too short or too long (max 500 chars)");
        char *error_str = cJSON_PrintUnformatted(error);
        send_packet(client_fd, ERROR_MSG, error_str);
        free(error_str);
        cJSON_Delete(error);
        return;
    }

    // Find room
    int room_index = -1;
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == room_id) {
            room_index = i;
            break;
        }
    }

    if (room_index == -1) {
        cJSON *error = cJSON_CreateObject();
        cJSON_AddStringToObject(error, "status", "fail");
        cJSON_AddStringToObject(error, "message", "Room not found");
        char *error_str = cJSON_PrintUnformatted(error);
        send_packet(client_fd, ERROR_MSG, error_str);
        free(error_str);
        cJSON_Delete(error);
        return;
    }

    // Find sender in room
    int sender_index = -1;
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (rooms[room_index].players[i].socket == client_fd) {
            sender_index = i;
            break;
        }
    }

    if (sender_index == -1) {
        cJSON *error = cJSON_CreateObject();
        cJSON_AddStringToObject(error, "status", "fail");
        cJSON_AddStringToObject(error, "message", "You are not in this room");
        char *error_str = cJSON_PrintUnformatted(error);
        send_packet(client_fd, ERROR_MSG, error_str);
        free(error_str);
        cJSON_Delete(error);
        return;
    }

    Player *sender = &rooms[room_index].players[sender_index];

    // Check if sender is alive (only alive players can chat during game)
    if (rooms[room_index].status == ROOM_PLAYING && !sender->is_alive) {
        cJSON *error = cJSON_CreateObject();
        cJSON_AddStringToObject(error, "status", "fail");
        cJSON_AddStringToObject(error, "message", "Dead players cannot chat");
        char *error_str = cJSON_PrintUnformatted(error);
        send_packet(client_fd, ERROR_MSG, error_str);
        free(error_str);
        cJSON_Delete(error);
        return;
    }

    // Determine chat type based on game phase and sender role
    const char *chat_type = "day"; // Default: day chat
    if (rooms[room_index].night_phase_active && sender->role == ROLE_WEREWOLF) {
        chat_type = "wolf";
    }

    printf("[SERVER] Chat (%s) from %s in room %d: %s\n", chat_type, sender->username, room_id, message);

    // Broadcast message to appropriate players
    cJSON *broadcast = cJSON_CreateObject();
    cJSON_AddStringToObject(broadcast, "username", sender->username);
    cJSON_AddStringToObject(broadcast, "message", message);
    cJSON_AddNumberToObject(broadcast, "room_id", room_id);
    cJSON_AddStringToObject(broadcast, "chat_type", chat_type);

    char *broadcast_str = cJSON_PrintUnformatted(broadcast);

    // Send to appropriate players based on chat type
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        int player_fd = rooms[room_index].players[i].socket;
        if (player_fd > 0) {
            // For wolf chat, only send to alive werewolves
            if (strcmp(chat_type, "wolf") == 0) {
                if (rooms[room_index].players[i].role == ROLE_WEREWOLF && rooms[room_index].players[i].is_alive) {
                    send_packet(player_fd, CHAT_BROADCAST, broadcast_str);
                    printf("[SERVER] Sent wolf chat to %s\n", rooms[room_index].players[i].username);
                }
            } else {
                // For day chat, send to ALL players (dead can spectate chat)
                send_packet(player_fd, CHAT_BROADCAST, broadcast_str);
                printf("[SERVER] Sent day chat to %s (alive: %d)\n", rooms[room_index].players[i].username, rooms[room_index].players[i].is_alive);
            }
        }
    }

    free(broadcast_str);
    cJSON_Delete(broadcast);
}
