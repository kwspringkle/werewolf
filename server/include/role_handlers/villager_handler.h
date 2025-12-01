#ifndef VILLAGER_HANDLER_H
#define VILLAGER_HANDLER_H

#include "cJSON.h"

// Get villager specific info
void villager_get_info(int room_index, int player_index, cJSON *info_obj);

#endif // VILLAGER_HANDLER_H
