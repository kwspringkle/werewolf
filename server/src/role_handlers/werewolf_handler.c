#include <stdio.h>
#include "role_handlers/werewolf_handler.h"
#include "types.h"
#include "cJSON.h"

extern Room rooms[MAX_ROOMS];

void werewolf_get_info(int room_index, int player_index, cJSON *info_obj) {
    cJSON_AddStringToObject(info_obj, "role_name", "Werewolf");
    cJSON_AddStringToObject(info_obj, "role_icon", "🐺");
    cJSON_AddStringToObject(info_obj, "role_description", 
        "You are a WEREWOLF! You know other werewolves. At night, discuss with your team to kill one villager. Your goal: Eliminate all villagers.");
    
    // Add werewolf team info
    cJSON *werewolf_team = cJSON_CreateArray();
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (i != player_index && rooms[room_index].players[i].role == ROLE_WEREWOLF) {
            cJSON_AddItemToArray(werewolf_team, 
                cJSON_CreateString(rooms[room_index].players[i].username));
        }
    }
    cJSON_AddItemToObject(info_obj, "werewolf_team", werewolf_team);
}
