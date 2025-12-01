#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#include "role_manager.h"
#include "packet_handler.h"
#include "room_manager.h"
#include "role_handlers/werewolf_handler.h"
#include "role_handlers/seer_handler.h"
#include "role_handlers/guard_handler.h"
#include "role_handlers/villager_handler.h"

extern Room rooms[MAX_ROOMS];

int validate_role_distribution(int num_players, int *num_werewolves, int *num_seer, 
                               int *num_guard, int *num_villagers) {
    // Luôn là 1 tiên tri và 1 bảo vệ 
    *num_seer = 1;
    *num_guard = 1;
    
    // Phân chia role: 
    // 6-8 players: 2 werewolves
    // 8-12 players: 3 werewolves
    if (num_players <= 8) {
        *num_werewolves = 2;
    } else {
        *num_werewolves = 3;
    }
    
    // Những người còn lại là dân làng
    *num_villagers = num_players - *num_werewolves - *num_seer - *num_guard;
    
    // Kiểm tra tính hợp lệ
    if (*num_villagers < 1) {
        return 0;
    }
    
    return 1;
}

cJSON* get_role_info_json(int room_index, int player_index) {
    cJSON *info = cJSON_CreateObject();
    PlayerRole role = rooms[room_index].players[player_index].role;
    
    switch(role) {
        case ROLE_WEREWOLF:
            werewolf_get_info(room_index, player_index, info);
            break;
        case ROLE_SEER:
            seer_get_info(room_index, player_index, info);
            break;
        case ROLE_GUARD:
            guard_get_info(room_index, player_index, info);
            break;
        default:
            villager_get_info(room_index, player_index, info);
            break;
    }
    
    return info;
}

cJSON* get_werewolf_team(int room_index, int player_index) {
    cJSON *team = cJSON_CreateArray();
    
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (i != player_index && rooms[room_index].players[i].role == ROLE_WEREWOLF) {
            cJSON_AddItemToArray(team, cJSON_CreateString(rooms[room_index].players[i].username));
        }
    }
    
    return team;
}

void send_role_info_to_player(int room_index, int player_index) {
    cJSON *role_response = cJSON_CreateObject();
    cJSON_AddStringToObject(role_response, "status", "success");
    cJSON_AddStringToObject(role_response, "message", "Game started");

    int role = rooms[room_index].players[player_index].role;
    cJSON_AddNumberToObject(role_response, "role", role);

    // Lấy thông tin cụ thể của vai trò
    cJSON *role_info = get_role_info_json(room_index, player_index);

    // Sao chép tất cả các trường từ role_info sang role_response
    cJSON *item = role_info->child;
    while (item) {
        if (item->type == cJSON_Array || item->type == cJSON_Object) {
            // Đối với mảng và đối tượng, sử dụng sao chép sâu
            cJSON *copy = cJSON_Duplicate(item, 1);
            cJSON_AddItemToObject(role_response, item->string, copy);
        } else {
            // Đối với các kiểu nguyên thủy, chỉ cần sao chép
            cJSON *copy = cJSON_Duplicate(item, 1);
            cJSON_AddItemToObject(role_response, item->string, copy);
        }
        item = item->next;
    }
    cJSON_Delete(role_info);

    char *role_str = cJSON_PrintUnformatted(role_response);
    send_packet(rooms[room_index].players[player_index].socket, GAME_START_RES_AND_ROLE, role_str);
    free(role_str);
    cJSON_Delete(role_response);
}
