#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <time.h>

#include "packet_handler.h"
#include "database.h"
#include "session_manager.h"
#include "room_manager.h"
#include "role_manager.h"
#include "cJSON.h"

void send_packet(int client_fd, uint16_t header, const char *payload) {
    uint32_t len = strlen(payload);

    uint16_t h = htons(header);
    uint32_t l = htonl(len);

    char *buffer = malloc(6 + len);
    if (!buffer) {
        fprintf(stderr, "Failed to allocate memory for packet\n");
        return;
    }

    memcpy(buffer,     &h, 2);
    memcpy(buffer + 2, &l, 4);
    memcpy(buffer + 6, payload, len);

    send(client_fd, buffer, 6 + len, 0);

    free(buffer);
}

void handle_ping(int client_fd, cJSON *json) {
    (void)json;
    cJSON *pong = cJSON_CreateObject();
    cJSON_AddStringToObject(pong, "type", "pong");
    char *pong_str = cJSON_PrintUnformatted(pong);

    send_packet(client_fd, PING, pong_str);

    free(pong_str);
    cJSON_Delete(pong);
}

void handle_register(int client_fd, cJSON *json){
    cJSON *user = cJSON_GetObjectItemCaseSensitive(json, "username");
    cJSON *pass = cJSON_GetObjectItemCaseSensitive(json, "password");

    cJSON *response = cJSON_CreateObject();

    if (!user || !pass || !cJSON_IsString(user) || !cJSON_IsString(pass)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Missing username or password");
    } else {
        char *hashed_pass = sha256_hash(pass->valuestring);

        if (!hashed_pass) {
            cJSON_AddStringToObject(response, "status", "error");
            cJSON_AddStringToObject(response, "message", "Server error");
        } else {
            char *escaped_user = escape_string(user->valuestring);
            char *escaped_hash = escape_string(hashed_pass);

            if (!escaped_user || !escaped_hash) {
                cJSON_AddStringToObject(response, "status", "error");
                cJSON_AddStringToObject(response, "message", "Server error");
                free(escaped_user);
                free(escaped_hash);
                free(hashed_pass);
            } else {
                char query[2048];
                snprintf(query, sizeof(query),
                         "INSERT INTO user (username, password_hash) VALUES ('%s', '%s')",
                         escaped_user, escaped_hash);

                if (mysql_query(conn, query)) {
                    cJSON_AddStringToObject(response, "status", "fail");
                    cJSON_AddStringToObject(response, "message", "Username already exists");
                } else {
                    cJSON_AddStringToObject(response, "status", "success");
                    printf("New user registered: %s\n", user->valuestring);
                }

                free(escaped_user);
                free(escaped_hash);
                free(hashed_pass);
            }
        }
    }

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, REGISTER_RES, res_str);

    free(res_str);
    cJSON_Delete(response);
}

void handle_login(int client_fd, cJSON *json){
    cJSON *user = cJSON_GetObjectItemCaseSensitive(json, "username");
    cJSON *pass = cJSON_GetObjectItemCaseSensitive(json, "password");

    cJSON *response = cJSON_CreateObject();

    if (!user || !pass || !cJSON_IsString(user) || !cJSON_IsString(pass)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Missing username or password");
    } else {
        char *hashed_pass = sha256_hash(pass->valuestring);

        if (!hashed_pass) {
            cJSON_AddStringToObject(response, "status", "error");
            cJSON_AddStringToObject(response, "message", "Server error");
        } else {
            char *escaped_user = escape_string(user->valuestring);
            char *escaped_hash = escape_string(hashed_pass);

            if (!escaped_user || !escaped_hash) {
                cJSON_AddStringToObject(response, "status", "error");
                cJSON_AddStringToObject(response, "message", "Server error");
                free(escaped_user);
                free(escaped_hash);
                free(hashed_pass);
            } else {
                char query[2048];
                snprintf(query, sizeof(query),
                         "SELECT user_id FROM user WHERE username='%s' AND password_hash='%s'",
                         escaped_user, escaped_hash);

                if (mysql_query(conn, query) == 0) {
                    MYSQL_RES *result = mysql_store_result(conn);
                    if (result && mysql_num_rows(result) > 0) {
                        MYSQL_ROW row = mysql_fetch_row(result);
                        int user_id = atoi(row[0]);

                        add_session(client_fd, user_id, user->valuestring);

                        cJSON_AddStringToObject(response, "status", "success");
                        cJSON_AddNumberToObject(response, "user_id", user_id);
                        cJSON_AddStringToObject(response, "username", user->valuestring);
                        printf("User login: %s (ID: %d)\n", user->valuestring, user_id);
                    } else {
                        cJSON_AddStringToObject(response, "status", "fail");
                        cJSON_AddStringToObject(response, "message", "Wrong username or password");
                    }
                    mysql_free_result(result);
                } else {
                    cJSON_AddStringToObject(response, "status", "error");
                    cJSON_AddStringToObject(response, "message", "Database error");
                }

                free(escaped_user);
                free(escaped_hash);
                free(hashed_pass);
            }
        }
    }

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, LOGIN_RES, res_str);

    free(res_str);
    cJSON_Delete(response);
}

void handle_get_rooms(int client_fd) {
    cJSON *response = cJSON_CreateArray();

    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id != 0) {
            cJSON *room_item = cJSON_CreateObject();
            cJSON_AddNumberToObject(room_item, "id", rooms[i].id);
            cJSON_AddStringToObject(room_item, "name", rooms[i].name);
            cJSON_AddNumberToObject(room_item, "current", rooms[i].current_players);
            cJSON_AddNumberToObject(room_item, "max", MAX_PLAYERS_PER_ROOM);
            cJSON_AddNumberToObject(room_item, "status", rooms[i].status);
            cJSON_AddItemToArray(response, room_item);
        }
    }

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, GET_ROOMS_RES, res_str);

    free(res_str);
    cJSON_Delete(response);
}

void handle_create_room(int client_fd, cJSON *json) {
    Session *session = find_session(client_fd);
    cJSON *response = cJSON_CreateObject();

    if (!session) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Please login first");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, CREATE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int current_room = get_user_room(client_fd);
    if (current_room != -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "You are already in a room");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, CREATE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    cJSON *room_name = cJSON_GetObjectItem(json, "room_name");
    if (!room_name || !cJSON_IsString(room_name)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid room name");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, CREATE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    size_t name_len = strlen(room_name->valuestring);
    if (name_len == 0 || name_len >= 50) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Room name must be 1-49 characters");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, CREATE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_index = -1;
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == 0) {
            room_index = i;
            break;
        }
    }

    if (room_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "No available rooms");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, CREATE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    rooms[room_index].id = room_index + 1;
    strncpy(rooms[room_index].name, room_name->valuestring, sizeof(rooms[room_index].name) - 1);
    rooms[room_index].name[49] = '\0'; 
    rooms[room_index].current_players = 1;
    rooms[room_index].status = ROOM_WAITING;
    rooms[room_index].host_socket = client_fd;

    rooms[room_index].players[0].socket = client_fd;
    rooms[room_index].players[0].user_id = session->user_id;
    strncpy(rooms[room_index].players[0].username, session->username, sizeof(rooms[room_index].players[0].username) - 1);

    cJSON_AddStringToObject(response, "status", "success");
    cJSON_AddNumberToObject(response, "room_id", rooms[room_index].id);
    cJSON_AddStringToObject(response, "room_name", rooms[room_index].name);

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, CREATE_ROOM_RES, res_str);
    free(res_str);
    cJSON_Delete(response);
    printf("Room created: %s by %s (user_id: %d)\n", room_name->valuestring, session->username, session->user_id);
}

void handle_join_room(int client_fd, cJSON *json) {
    Session *session = find_session(client_fd);

    cJSON *response = cJSON_CreateObject();

    if (!session) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Please login first");
        send_packet(client_fd, JOIN_ROOM_RES, cJSON_PrintUnformatted(response));
        cJSON_Delete(response);
        return;
    }

    int current_room = get_user_room(client_fd);
    if (current_room != -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "You are already in a room");
        send_packet(client_fd, JOIN_ROOM_RES, cJSON_PrintUnformatted(response));
        cJSON_Delete(response);
        return;
    }

    cJSON *room_id_obj = cJSON_GetObjectItemCaseSensitive(json, "room_id");
    if (!room_id_obj || !cJSON_IsNumber(room_id_obj)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid or missing room_id");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, JOIN_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_id = room_id_obj->valueint;

    if (room_id < 1 || room_id > MAX_ROOMS) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid room_id");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, JOIN_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_index = -1;
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == room_id) {
            room_index = i;
            break;
        }
    }

    if (room_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Room not found");
        send_packet(client_fd, JOIN_ROOM_RES, cJSON_PrintUnformatted(response));
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].status == ROOM_PLAYING) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Game already started");
        send_packet(client_fd, JOIN_ROOM_RES, cJSON_PrintUnformatted(response));
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].current_players >= MAX_PLAYERS_PER_ROOM) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Room is full");
        send_packet(client_fd, JOIN_ROOM_RES, cJSON_PrintUnformatted(response));
        cJSON_Delete(response);
        return;
    }

    int idx = rooms[room_index].current_players;
    rooms[room_index].players[idx].socket = client_fd;
    rooms[room_index].players[idx].user_id = session->user_id;
    strncpy(rooms[room_index].players[idx].username, session->username, sizeof(rooms[room_index].players[idx].username) - 1);
    rooms[room_index].players[idx].username[49] = '\0';
    rooms[room_index].current_players++;

    cJSON_AddStringToObject(response, "status", "success");
    cJSON_AddNumberToObject(response, "is_host", 0);
    cJSON_AddNumberToObject(response, "room_id", rooms[room_index].id);
    cJSON_AddStringToObject(response, "room_name", rooms[room_index].name);

    cJSON *player_list = cJSON_CreateArray();
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        cJSON *p = cJSON_CreateObject();
        cJSON_AddStringToObject(p, "username", rooms[room_index].players[i].username);
        cJSON_AddItemToArray(player_list, p);
    }
    cJSON_AddItemToObject(response, "players", player_list);

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, JOIN_ROOM_RES, res_str);
    free(res_str);
    cJSON_Delete(response);

    cJSON *update = cJSON_CreateObject();
    cJSON_AddStringToObject(update, "type", "player_joined");
    cJSON_AddStringToObject(update, "username", session->username);
    cJSON_AddNumberToObject(update, "current_players", rooms[room_index].current_players);

    char *update_str = cJSON_PrintUnformatted(update);
    broadcast_room(room_index, ROOM_STATUS_UPDATE, update_str);
    free(update_str);
    cJSON_Delete(update);

    printf("Player %s joined room %d\n", session->username, room_id);
}

void handle_disconnect(int client_fd) {
    Session *session = find_session(client_fd);

    if (session) {
        printf("User %s disconnected (socket: %d)\n", session->username, client_fd);

        int room_index = get_user_room(client_fd);
        if (room_index != -1) {
            int player_index = -1;
            for (int i = 0; i < rooms[room_index].current_players; i++) {
                if (rooms[room_index].players[i].socket == client_fd) {
                    player_index = i;
                    break;
                }
            }

            if (player_index != -1) {
                char username[50];
                strncpy(username, rooms[room_index].players[player_index].username, sizeof(username) - 1);

                // Check if game is in progress
                if (rooms[room_index].status == ROOM_PLAYING) {
                    // Mark player as dead instead of removing them
                    rooms[room_index].players[player_index].is_alive = 0;
                    printf("Player %s in room %d marked as dead (disconnected during game)\n", 
                           username, rooms[room_index].id);
                    
                    // Broadcast player death to room
                    cJSON *update = cJSON_CreateObject();
                    cJSON_AddStringToObject(update, "type", "player_disconnected");
                    cJSON_AddStringToObject(update, "username", username);
                    cJSON_AddStringToObject(update, "message", "Player disconnected and is considered dead");
                    cJSON_AddBoolToObject(update, "game_started", true);  // Game đã start

                    char *update_str = cJSON_PrintUnformatted(update);
                    broadcast_room(room_index, ROOM_STATUS_UPDATE, update_str);
                    free(update_str);
                    cJSON_Delete(update);
                    
                    // TODO: Check win condition after disconnect
                } else {
                    // Game not started yet, remove player normally
                    for (int i = player_index; i < rooms[room_index].current_players - 1; i++) {
                        rooms[room_index].players[i] = rooms[room_index].players[i + 1];
                    }
                    rooms[room_index].current_players--;

                    if (rooms[room_index].current_players == 0) {
                        printf("Room %d is now empty and will be deleted\n", rooms[room_index].id);
                        rooms[room_index].id = 0;
                        rooms[room_index].name[0] = '\0';
                        rooms[room_index].status = ROOM_WAITING;
                        rooms[room_index].host_socket = 0;
                    } else {
                        int host_changed = 0;
                        char new_host_username[50] = "";
                        
                        if (rooms[room_index].host_socket == client_fd) {
                            rooms[room_index].host_socket = rooms[room_index].players[0].socket;
                            strncpy(new_host_username, rooms[room_index].players[0].username, 49);
                            host_changed = 1;
                            printf("Host changed to %s in room %d\n",
                                   new_host_username, rooms[room_index].id);
                        }

                        cJSON *update = cJSON_CreateObject();
                        cJSON_AddStringToObject(update, "type", "player_disconnected");
                        cJSON_AddStringToObject(update, "username", username);
                        cJSON_AddNumberToObject(update, "current_players", rooms[room_index].current_players);
                        cJSON_AddBoolToObject(update, "game_started", false);  // Game chưa start
                        
                        // Thêm thông tin host mới nếu có thay đổi
                        if (host_changed) {
                            cJSON_AddStringToObject(update, "new_host", new_host_username);
                        }

                        char *update_str = cJSON_PrintUnformatted(update);
                        broadcast_room(room_index, ROOM_STATUS_UPDATE, update_str);
                        free(update_str);
                        cJSON_Delete(update);
                    }
                }
            }
        }

        remove_session(client_fd);
    } else {
        printf("Client %d disconnected (not logged in)\n", client_fd);
    }
}

void handle_leave_room(int client_fd, cJSON *json) {
    (void)json;
    Session *session = find_session(client_fd);
    cJSON *response = cJSON_CreateObject();

    if (!session) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Please login first");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, LEAVE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_index = get_user_room(client_fd);
    if (room_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "You are not in any room");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, LEAVE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    // If game is playing, mark as dead instead of leaving
    if (rooms[room_index].status == ROOM_PLAYING) {
        int player_index = -1;
        for (int i = 0; i < rooms[room_index].current_players; i++) {
            if (rooms[room_index].players[i].socket == client_fd) {
                player_index = i;
                break;
            }
        }
        
        if (player_index != -1) {
            rooms[room_index].players[player_index].is_alive = 0;
            
            cJSON_AddStringToObject(response, "status", "success");
            cJSON_AddStringToObject(response, "message", "You left the game and are considered dead");
            char *res_str = cJSON_PrintUnformatted(response);
            send_packet(client_fd, LEAVE_ROOM_RES, res_str);
            free(res_str);
            cJSON_Delete(response);
            
            // Broadcast to room
            cJSON *update = cJSON_CreateObject();
            cJSON_AddStringToObject(update, "type", "player_disconnected");
            cJSON_AddStringToObject(update, "username", rooms[room_index].players[player_index].username);
            cJSON_AddStringToObject(update, "message", "Player left and is considered dead");
            
            char *update_str = cJSON_PrintUnformatted(update);
            broadcast_room(room_index, ROOM_STATUS_UPDATE, update_str);
            free(update_str);
            cJSON_Delete(update);
            
            printf("Player %s left room %d during game (marked as dead)\n", 
                   rooms[room_index].players[player_index].username, rooms[room_index].id);
        }
        return;
    }

    int player_index = -1;
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (rooms[room_index].players[i].socket == client_fd) {
            player_index = i;
            break;
        }
    }

    if (player_index == -1){
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "You are not in this room");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, LEAVE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    char username [50];
    strncpy(username, rooms[room_index].players[player_index].username, sizeof(username) - 1);
    username[49] = '\0';

    // Check if this player is host BEFORE removing
    int was_host = (rooms[room_index].host_socket == client_fd);
    int host_changed = 0;
    char new_host_username[50] = "";

    // Remove player from list
    for (int i = player_index; i < rooms[room_index].current_players - 1; i++) {
        rooms[room_index].players[i] = rooms[room_index].players[i + 1];
    }
    rooms[room_index].current_players--;

    printf("Player %s left room %d\n", username, rooms[room_index].id);

    // Send success response to leaving player
    cJSON_AddStringToObject(response, "status", "success");
    cJSON_AddStringToObject(response, "message", "Left room successfully");
    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, LEAVE_ROOM_RES, res_str);
    free(res_str);
    cJSON_Delete(response);

    // Check if room is empty
    if (rooms[room_index].current_players == 0) {
        printf("Room %d is now empty and will be deleted\n", rooms[room_index].id);
        rooms[room_index].id = 0;
        rooms[room_index].name[0] = '\0';
        rooms[room_index].status = ROOM_WAITING;
        rooms[room_index].host_socket = 0;
        return;  // No need to broadcast if room is empty
    }

    // If the host left, assign new host
    if (was_host) {
        rooms[room_index].host_socket = rooms[room_index].players[0].socket;
        strncpy(new_host_username, rooms[room_index].players[0].username, 49);
        new_host_username[49] = '\0';
        host_changed = 1;
        printf("Host changed to %s in room %d\n", new_host_username, rooms[room_index].id);
    }

    // Broadcast to remaining players
    cJSON *update = cJSON_CreateObject();
    cJSON_AddStringToObject(update, "type", "player_left");
    cJSON_AddStringToObject(update, "username", username);
    cJSON_AddNumberToObject(update, "current_players", rooms[room_index].current_players);
    
    // Add new host info if changed
    if (host_changed) {
        cJSON_AddStringToObject(update, "new_host", new_host_username);
    }

    char *update_str = cJSON_PrintUnformatted(update);
    broadcast_room(room_index, ROOM_STATUS_UPDATE, update_str);
    free(update_str);
    cJSON_Delete(update);
}

void handle_get_room_info(int client_fd, cJSON *json) {
    cJSON *response = cJSON_CreateObject();

    cJSON *room_id_obj = cJSON_GetObjectItemCaseSensitive(json, "room_id");
    if (!room_id_obj || !cJSON_IsNumber(room_id_obj)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid room ID");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, GET_ROOM_INFO_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_id = room_id_obj->valueint;

    int room_index = -1;
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == room_id) {
            room_index = i;
            break;
        }
    }

    if (room_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Room not found");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, GET_ROOM_INFO_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    cJSON_AddStringToObject(response, "status", "success");
    cJSON_AddNumberToObject(response, "room_id", rooms[room_index].id);
    cJSON_AddStringToObject(response, "room_name", rooms[room_index].name);
    cJSON_AddNumberToObject(response, "current_players", rooms[room_index].current_players);
    cJSON_AddNumberToObject(response, "max_players", MAX_PLAYERS_PER_ROOM);
    cJSON_AddNumberToObject(response, "status", rooms[room_index].status);

    cJSON *players = cJSON_CreateArray();
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        cJSON *player = cJSON_CreateObject();
        cJSON_AddStringToObject(player, "username", rooms[room_index].players[i].username);
        cJSON_AddNumberToObject(player, "user_id", rooms[room_index].players[i].user_id);

        int is_host = (rooms[room_index].players[i].socket == rooms[room_index].host_socket) ? 1 : 0;
        cJSON_AddNumberToObject(player, "is_host", is_host);

        cJSON_AddItemToArray(players, player);
    }

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, GET_ROOM_INFO_RES, res_str);
    free(res_str);
    cJSON_Delete(response);
}

void handle_start_game(int client_fd, cJSON *json) {
    cJSON *response = cJSON_CreateObject();

    cJSON *room_id_obj = cJSON_GetObjectItemCaseSensitive(json, "room_id");
    if (!room_id_obj || !cJSON_IsNumber(room_id_obj)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid or missing room_id");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }
    int room_id = room_id_obj->valueint;

    if (room_id < 1 || room_id > MAX_ROOMS) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid room_id");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_index = -1;
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == room_id) {
            room_index = i;
            break;
        }
    }

    if (room_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Room not found");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].host_socket != client_fd) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Only host can start the game");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].current_players < MIN_PLAYERS_TO_START) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Need at least 6 players to start");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].status == ROOM_PLAYING) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Game already started");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    rooms[room_index].status = ROOM_PLAYING;

    // Calculate role distribution
    int num_players = rooms[room_index].current_players;
    int num_werewolves, num_seer, num_guard, num_villagers;
    
    if (!validate_role_distribution(num_players, &num_werewolves, &num_seer, &num_guard, &num_villagers)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid player count for role distribution");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        rooms[room_index].status = ROOM_WAITING;
        return;
    }
    
    // Create role array
    int roles[MAX_PLAYERS_PER_ROOM];
    int role_index = 0;
    
    // Add werewolves
    for (int i = 0; i < num_werewolves; i++) {
        roles[role_index++] = ROLE_WEREWOLF;
    }
    // Add seer
    roles[role_index++] = ROLE_SEER;
    // Add guard
    roles[role_index++] = ROLE_GUARD;
    // Add villagers
    for (int i = 0; i < num_villagers; i++) {
        roles[role_index++] = ROLE_VILLAGER;
    }
    
    // Shuffle roles using Fisher-Yates algorithm
    srand(time(NULL));
    for (int i = num_players - 1; i > 0; i--) {
        int j = rand() % (i + 1);
        int temp = roles[i];
        roles[i] = roles[j];
        roles[j] = temp;
    }
    
    // Assign shuffled roles to players and send individual role info
    printf("\n=== ROLE DISTRIBUTION ===\n");
    for (int i = 0; i < num_players; i++) {
        rooms[room_index].players[i].role = roles[i];
        rooms[room_index].players[i].is_alive = 1;
        
        // Send role to each player using role_manager
        send_role_info_to_player(room_index, i);
    }
    printf("=== END ROLE DISTRIBUTION ===\n\n");
    
    cJSON_Delete(response);

    printf("✓ Game started in room %d with %d players\n", 
           room_id, rooms[room_index].current_players);
    printf("  Role distribution: %d Werewolves, 1 Seer, 1 Guard, %d Villagers\n", 
           num_werewolves, num_villagers);
}

void process_packet(int client_fd, uint16_t header, const char *payload) {
    cJSON *json = cJSON_Parse(payload);
    if (!json) {
        printf("Invalid JSON payload from client %d\n", client_fd);
        return;
    }

    switch (header) {
        case REGISTER_REQ:
            handle_register(client_fd, json);
            break;
        case LOGIN_REQ:
            handle_login(client_fd, json);
            break;
        case GET_ROOMS_REQ:
            handle_get_rooms(client_fd);
            break;
        case CREATE_ROOM_REQ:
            handle_create_room(client_fd, json);
            break;
        case JOIN_ROOM_REQ:
            handle_join_room(client_fd, json);
            break;
        case START_GAME_REQ:
            handle_start_game(client_fd, json);
            break;
        case LEAVE_ROOM_REQ:
            handle_leave_room(client_fd, json);
            break;
        case LOGOUT_REQ:
            handle_disconnect(client_fd);  // Logout = disconnect
            break;
        case GET_ROOM_INFO_REQ:
            handle_get_room_info(client_fd, json);
            break;
        case PING:
            handle_ping(client_fd, json);
            break;
        default:
            printf("Unknown packet header: %d\n", header);
            break;
    }

    cJSON_Delete(json);
}