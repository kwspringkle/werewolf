#ifndef PACKET_HANDLER_H
#define PACKET_HANDLER_H
#include "cJSON.h" 
#include "types.h"
#include <stdint.h>

void send_packet(int client_fd, uint16_t header, const char *payload);
void handle_disconnect(int client_fd);
void process_packet(int client_fd, uint16_t header, const char *payload);

// Các hàm xử lý packet cụ thể
void handle_register(int client_fd, cJSON *json);
void handle_login(int client_fd, cJSON *json);
void handle_ping(int client_fd, cJSON *json);
void handle_get_rooms(int client_fd);
void handle_create_room(int client_fd, cJSON *json);
void handle_join_room(int client_fd, cJSON *json);
void handle_leave_room(int client_fd, cJSON *json);
void handle_get_room_info(int client_fd, cJSON *json);
void handle_start_game(int client_fd, cJSON *json);

#endif