#ifndef SEER_HANDLER_H
#define SEER_HANDLER_H

#include "cJSON.h"

// Get seer specific info
void seer_get_info(int room_index, int player_index, cJSON *info_obj);
// Handle a seer check request. Fills `response` with status/message/result.
void seer_handle_check(int room_index, int requester_index, const char *target_username, cJSON *response);
// Handle a seer packet coming from a socket (delegates to seer_handle_check and sends result)
void seer_handle_packet(int client_fd, cJSON *json);

#endif // SEER_HANDLER_H
