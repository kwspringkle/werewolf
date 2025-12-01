#ifndef SEER_HANDLER_H
#define SEER_HANDLER_H

#include "cJSON.h"

// Get seer specific info
void seer_get_info(int room_index, int player_index, cJSON *info_obj);

#endif // SEER_HANDLER_H
