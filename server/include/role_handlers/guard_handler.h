#ifndef GUARD_HANDLER_H
#define GUARD_HANDLER_H

#include "cJSON.h"


// Get guard specific info
void guard_get_info(int room_index, int player_index, cJSON *info_obj);
void guard_handle_packet(int client_fd, cJSON *json);
void guard_handle_protect(int room_index, int requester_index, const char *target_username, cJSON *response);

#endif // GUARD_HANDLER_H
