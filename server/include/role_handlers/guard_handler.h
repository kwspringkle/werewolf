#ifndef GUARD_HANDLER_H
#define GUARD_HANDLER_H

#include "cJSON.h"

// Get guard specific info
void guard_get_info(int room_index, int player_index, cJSON *info_obj);

#endif // GUARD_HANDLER_H
