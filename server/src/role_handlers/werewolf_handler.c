#include <string.h>
#include <time.h>
#include "protocol.h"
#include "packet_handler.h"

// Helper: Đếm số vote cho từng username
static void count_wolf_votes(Room *room, int *vote_counts, int *max_votes, int *victim_index) {
    int n = room->current_players;
    memset(vote_counts, 0, sizeof(int) * n);
    *max_votes = 0;
    *victim_index = -1;
    for (int i = 0; i < n; i++) {
        if (room->players[i].role != ROLE_WEREWOLF || !room->players[i].is_alive) continue;
        // Lưu lựa chọn vào player struct nếu muốn, hoặc dùng mảng tạm
        // Ở đây giả sử room->players[i].username chứa tên mục tiêu
        // (Bạn có thể mở rộng struct Player nếu muốn lưu vote)
    }
    // Đếm vote (giả sử có mảng votes[] chứa index mục tiêu của từng sói)
    // Ở đây chỉ là khung, bạn cần lưu lại vote của từng sói khi nhận gói tin
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

    // NO RESPONSE SENT - client doesn't handle WOLF_KILL_RES

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
        int max_votes = 0, victim_index = -1;
        for (int i = 0; i < n; i++) {
            if (vote_tally[i] > max_votes) {
                max_votes = vote_tally[i];
                victim_index = i;
            }
        }
        // Kiểm tra hợp lệ
        if (victim_index != -1 && max_votes > 0) {
            Player *victim = &rooms[room_index].players[victim_index];
            // Kiểm tra đã chết chưa
            if (victim->is_alive) {
                // Kiểm tra có được bảo vệ không
                if (strlen(rooms[room_index].guard_protected_username) > 0 &&
                    strcmp(victim->username, rooms[room_index].guard_protected_username) == 0) {
                    // Được bảo vệ, không chết
                    printf("[SERVER] %s was protected by guard, survived the attack\n", victim->username);
                } else {
                    // Không được bảo vệ, set chết
                    victim->is_alive = 0;
                    printf("[SERVER] %s was killed by wolves (votes: %d)\n", victim->username, max_votes);
                }
            }
        } else {
            printf("[SERVER] No valid victim from wolf votes (max_votes: %d)\n", max_votes);
        }
        rooms[room_index].wolf_kill_done = 1;
        
        // Kết thúc night phase và chuyển sang day phase
        rooms[room_index].night_phase_active = 0;
        
        // Collect danh sách người chết (bao gồm cả disconnected users)
        cJSON *dead_players = cJSON_CreateArray();
        for (int j = 0; j < rooms[room_index].current_players; j++) {
            if (!rooms[room_index].players[j].is_alive) {
                cJSON_AddItemToArray(dead_players, cJSON_CreateString(rooms[room_index].players[j].username));
                printf("[SERVER] Player %s is dead (included in death list)\n", rooms[room_index].players[j].username);
            }
        }
        
        // Broadcast day phase start to all players (KHÔNG disconnect/kick ai cả)
        cJSON *day_notif = cJSON_CreateObject();
        cJSON_AddStringToObject(day_notif, "type", "phase_day");
        cJSON_AddStringToObject(day_notif, "message", "All wolves voted, night phase ended, day phase begins");
        cJSON_AddItemToObject(day_notif, "dead_players", dead_players);
        char *day_notif_str = cJSON_PrintUnformatted(day_notif);
        printf("[SERVER] All wolves voted in room %d, broadcasting PHASE_DAY (304) with %d dead players\n", 
               rooms[room_index].id, cJSON_GetArraySize(dead_players));
        broadcast_room(room_index, PHASE_DAY, day_notif_str);
        free(day_notif_str);
        cJSON_Delete(day_notif);
    }
}
#include <stdio.h>
#include "role_handlers/werewolf_handler.h"
#include "types.h"
#include "cJSON.h"
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
