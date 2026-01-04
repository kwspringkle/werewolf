#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stdlib.h>
#include "protocol.h"
#include "packet_handler.h"
#include "cJSON.h"
#include "role_handlers/werewolf_handler.h"
#include "types.h"
#include "room_manager.h"

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

// Xử lý gói tin sói cắn
void werewolf_handle_packet(int client_fd, cJSON *json) {
    cJSON *room_id_obj = cJSON_GetObjectItemCaseSensitive(json, "room_id");
    cJSON *target_obj = cJSON_GetObjectItemCaseSensitive(json, "target_username");

    if (!room_id_obj || !cJSON_IsNumber(room_id_obj) || !target_obj || !cJSON_IsString(target_obj)) {
        printf("[SERVER] Wolf kill request missing room_id or target_username\n");
        return;
    }

    int room_id = room_id_obj->valueint;
    int room_index = -1;
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == room_id) {
            room_index = i;
            break;
        }
    }

    if (room_index == -1) {
        printf("[SERVER] Wolf kill request: room %d not found\n", room_id);
        return;
    }

    // Tìm người đang gửi request
    int requester_index = -1;
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (rooms[room_index].players[i].socket == client_fd) {
            requester_index = i;
            break;
        }
    }

    if (requester_index == -1) {
        printf("[SERVER] Wolf kill request: sender not in room %d\n", room_id);
        return;
    }

    Player *requester = &rooms[room_index].players[requester_index];
    if (!requester->is_alive || requester->role != ROLE_WEREWOLF) {
        printf("[SERVER] Wolf kill request from non-wolf or dead player: %s\n", requester->username);
        return;
    }

    if (!rooms[room_index].night_phase_active) {
        printf("[SERVER] Wolf kill request when night phase not active\n");
        return;
    }

    time_t now = time(NULL);
    if (rooms[room_index].wolf_deadline != 0 && now > rooms[room_index].wolf_deadline) {
        printf("[SERVER] Wolf kill request after deadline\n");
        return;
    }

    // Kiểm tra target còn sống không
    int target_index = -1;
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (strcmp(rooms[room_index].players[i].username, target_obj->valuestring) == 0) {
            target_index = i; break;
        }
    }
    if (target_index == -1) {
        printf("[SERVER] Wolf kill request: target %s not found\n", target_obj->valuestring);
        return;
    }
    if (!rooms[room_index].players[target_index].is_alive) {
        printf("[SERVER] Wolf kill request: target %s already dead\n", target_obj->valuestring);
        return;
    }

    // Lưu lại vote của sói
    int n = rooms[room_index].current_players;
    int wolf_index = requester_index;
    strncpy(rooms[room_index].wolf_votes[wolf_index], rooms[room_index].players[target_index].username, 49);
    rooms[room_index].wolf_votes[wolf_index][49] = '\0';

    printf("[SERVER] Wolf %s voted to kill %s\n", requester->username, target_obj->valuestring);

    // Đếm số sói còn sống
    int alive_wolves = 0;
    for (int i = 0; i < n; i++) {
        if (rooms[room_index].players[i].role == ROLE_WEREWOLF && rooms[room_index].players[i].is_alive)
            alive_wolves++;
    }

    // Đếm số sói đã vote
    int wolf_vote_count = 0;
    for (int i = 0; i < n; i++) {
        if (rooms[room_index].players[i].role == ROLE_WEREWOLF && rooms[room_index].players[i].is_alive && strlen(rooms[room_index].wolf_votes[i]) > 0)
            wolf_vote_count++;
    }
    rooms[room_index].wolf_vote_count = wolf_vote_count;

    // Gửi compact confirmation khi vote (chỉ gửi cho wolf vừa submit)
    cJSON *vote_conf = cJSON_CreateObject();
    cJSON_AddStringToObject(vote_conf, "type", "wolf_vote_received");
    char *vote_conf_str = cJSON_PrintUnformatted(vote_conf);
    send_packet(client_fd, WOLF_KILL_RES, vote_conf_str);
    free(vote_conf_str);
    cJSON_Delete(vote_conf);

    // Nếu tất cả sói còn sống đã vote, tổng hợp kết quả
    if (wolf_vote_count == alive_wolves && !rooms[room_index].wolf_kill_done) {
        // Đếm số vote cho từng username
        int vote_tally[MAX_PLAYERS_PER_ROOM] = {0};
        for (int i = 0; i < n; i++) {
            if (rooms[room_index].players[i].role == ROLE_WEREWOLF && rooms[room_index].players[i].is_alive) {
                char *voted_name = rooms[room_index].wolf_votes[i];
                for (int j = 0; j < n; j++) {
                    if (strlen(voted_name) > 0 && strcmp(rooms[room_index].players[j].username, voted_name) == 0)
                        vote_tally[j]++;
                }
            }
        }
        // Tìm người bị vote nhiều nhất
        int max_votes = 0;
        int victim_candidates[MAX_PLAYERS_PER_ROOM];
        int candidate_count = 0;
        
        for (int i = 0; i < n; i++) {
            if (vote_tally[i] > max_votes) {
                max_votes = vote_tally[i];
                candidate_count = 0;
                victim_candidates[candidate_count++] = i;
            } else if (vote_tally[i] == max_votes && max_votes > 0) {
                victim_candidates[candidate_count++] = i;
            }
        }
        
        // Xử lý kết quả vote
        int victim_index = -1;
        const char *result = "no_kill";
        const char *target_id = NULL;
        
        if (candidate_count > 0 && max_votes > 0) {
            // Nếu hòa (nhiều người cùng số vote cao nhất), random chọn 1
            if (candidate_count > 1) {
                srand((unsigned int)time(NULL) + room_index); // Seed với time + room để đảm bảo random
                victim_index = victim_candidates[rand() % candidate_count];
                printf("[SERVER] Tie detected (%d candidates), randomly selected: %s\n", 
                       candidate_count, rooms[room_index].players[victim_index].username);
            } else {
                victim_index = victim_candidates[0];
            }
            
            Player *victim = &rooms[room_index].players[victim_index];
            target_id = victim->username;
            
            // Kiểm tra đã chết chưa
            if (victim->is_alive) {
                // Kiểm tra có được bảo vệ không
                if (strlen(rooms[room_index].guard_protected_username) > 0 &&
                    strcmp(victim->username, rooms[room_index].guard_protected_username) == 0) {
                    // Được bảo vệ, không chết
                    result = "no_kill";
                    printf("[SERVER] %s was protected by guard, survived the attack\n", victim->username);
                } else {
                    // Không được bảo vệ, set chết
                    result = "killed";
                    victim->is_alive = 0;
                    printf("[SERVER] %s was killed by wolves (votes: %d)\n", victim->username, max_votes);
                }
            } else {
                result = "no_kill";
                printf("[SERVER] Target %s already dead, no kill\n", victim->username);
            }
        } else {
            printf("[SERVER] No valid victim from wolf votes (max_votes: %d)\n", max_votes);
        }
        
        rooms[room_index].wolf_kill_done = 1;
        
        // Kết thúc night phase
        rooms[room_index].night_phase_active = 0;
        
        // Gửi compact result thay vì large dead_players array
        cJSON *result_obj = cJSON_CreateObject();
        cJSON_AddStringToObject(result_obj, "type", "phase_day");
        cJSON_AddStringToObject(result_obj, "result", result);
        if (target_id != NULL && strcmp(result, "killed") == 0) {
            cJSON_AddStringToObject(result_obj, "targetId", target_id);
        }
        char *result_str = cJSON_PrintUnformatted(result_obj);
        printf("[SERVER] All wolves voted in room %d, broadcasting compact PHASE_DAY (304): result=%s%s%s\n", 
               rooms[room_index].id, result, 
               (target_id && strcmp(result, "killed") == 0) ? ", target=" : "",
               (target_id && strcmp(result, "killed") == 0) ? target_id : "");
        broadcast_room(room_index, PHASE_DAY, result_str);
        free(result_str);
        cJSON_Delete(result_obj);
    }
}




