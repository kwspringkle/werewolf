#ifndef WEREWOLF_HANDLER_H
#define WEREWOLF_HANDLER_H

#include "cJSON.h"

// Get werewolf specific info
void werewolf_get_info(int room_index, int player_index, cJSON *info_obj);

#endif // WEREWOLF_HANDLER_H
