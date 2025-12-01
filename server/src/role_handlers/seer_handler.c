#include <stdio.h>
#include "role_handlers/seer_handler.h"
#include "cJSON.h"

void seer_get_info(int room_index, int player_index, cJSON *info_obj) {
    cJSON_AddStringToObject(info_obj, "role_name", "Seer");
    cJSON_AddStringToObject(info_obj, "role_icon", "🔮");
    cJSON_AddStringToObject(info_obj, "role_description",
        "You are the SEER! Each night, you can check one player to know if they are a werewolf or not. Use your knowledge wisely to guide the village.");
}
