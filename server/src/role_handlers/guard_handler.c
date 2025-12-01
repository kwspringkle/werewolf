#include <stdio.h>
#include "role_handlers/guard_handler.h"
#include "cJSON.h"

void guard_get_info(int room_index, int player_index, cJSON *info_obj) {
    cJSON_AddStringToObject(info_obj, "role_name", "Guard");
    cJSON_AddStringToObject(info_obj, "role_icon", "🛡️");
    cJSON_AddStringToObject(info_obj, "role_description",
        "You are the GUARD! Each night, you can protect one player from werewolf attacks. Choose wisely to save the village.");
}
