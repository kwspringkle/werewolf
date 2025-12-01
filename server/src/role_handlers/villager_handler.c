#include <stdio.h>
#include "role_handlers/villager_handler.h"
#include "cJSON.h"

void villager_get_info(int room_index, int player_index, cJSON *info_obj) {
    cJSON_AddStringToObject(info_obj, "role_name", "Villager");
    cJSON_AddStringToObject(info_obj, "role_icon", "👨");
    cJSON_AddStringToObject(info_obj, "role_description",
        "You are a VILLAGER! You have no special abilities, but your vote matters. Work with others to find and eliminate the werewolves.");
}
