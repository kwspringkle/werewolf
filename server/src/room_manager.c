#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "room_manager.h"
#include "session_manager.h"
#include "packet_handler.h"
#include "cJSON.h"
#include "protocol.h"
#include <time.h>

// Duration cho mỗi phase (giây)
#define SEER_PHASE_DURATION 30
#define GUARD_PHASE_DURATION 30
#define WOLF_PHASE_DURATION 30
#define TOTAL_NIGHT_PHASE_DURATION (SEER_PHASE_DURATION + GUARD_PHASE_DURATION + WOLF_PHASE_DURATION)

Room rooms[MAX_ROOMS];

void init_rooms() {
    for (int i = 0; i < MAX_ROOMS; i++) {
        rooms[i].id = 0;
        rooms[i].name[0] = '\0';
        rooms[i].current_players = 0;
        rooms[i].status = ROOM_WAITING;
        rooms[i].host_socket = 0;
        rooms[i].night_phase_active = 0;
        rooms[i].seer_deadline = 0;
        rooms[i].seer_choice_made = 0;
        rooms[i].seer_chosen_target[0] = '\0';
        rooms[i].role_card_done_count = 0;
        rooms[i].role_card_total = 0;
        rooms[i].role_card_start_time = 0;
    }
}

void start_night_phase(int room_index, int duration_seconds) {
    if (room_index < 0 || room_index >= MAX_ROOMS) return;

    rooms[room_index].night_phase_active = 1;
    rooms[room_index].role_card_start_time = 0; // Reset to prevent timeout check from triggering again
    time_t now = time(NULL);
    
    // Tính deadline cho từng phase: seer -> guard -> wolf (tuần tự)
    rooms[room_index].seer_deadline = now + SEER_PHASE_DURATION;
    rooms[room_index].guard_deadline = rooms[room_index].seer_deadline + GUARD_PHASE_DURATION;
    rooms[room_index].wolf_deadline = rooms[room_index].guard_deadline + WOLF_PHASE_DURATION;
    
    // Total duration = tổng của tất cả các phase
    int total_duration = TOTAL_NIGHT_PHASE_DURATION;
    
    printf("[SERVER] Starting night phase for room %d:\n", rooms[room_index].id);
    printf("  - Seer deadline: %ld (now + %d seconds)\n", rooms[room_index].seer_deadline, SEER_PHASE_DURATION);
    printf("  - Guard deadline: %ld (seer_deadline + %d seconds)\n", rooms[room_index].guard_deadline, GUARD_PHASE_DURATION);
    printf("  - Wolf deadline: %ld (guard_deadline + %d seconds)\n", rooms[room_index].wolf_deadline, WOLF_PHASE_DURATION);
    printf("  - Total duration: %d seconds\n", total_duration);
    
    // In role của từng người chơi
    printf("[SERVER] Room %d - Player roles:\n", rooms[room_index].id);
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        const char *role_name = "UNKNOWN";
        switch (rooms[room_index].players[i].role) {
            case 0: role_name = "VILLAGER"; break;
            case 1: role_name = "WEREWOLF"; break;
            case 2: role_name = "SEER"; break;
            case 3: role_name = "GUARD"; break;
        }
        printf("  - %s: %s (alive: %d)\n", 
               rooms[room_index].players[i].username, 
               role_name,
               rooms[room_index].players[i].is_alive);
    }
    
    rooms[room_index].seer_choice_made = 0;
    rooms[room_index].seer_chosen_target[0] = '\0';
    rooms[room_index].guard_choice_made = 0;
    rooms[room_index].guard_protected_username[0] = '\0';
    rooms[room_index].wolf_vote_count = 0;
    rooms[room_index].wolf_kill_done = 0;
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        rooms[room_index].wolf_votes[i][0] = '\0';
    }

    cJSON *notif = cJSON_CreateObject();
    cJSON_AddStringToObject(notif, "type", "phase_night");
    cJSON_AddNumberToObject(notif, "duration", total_duration);
    cJSON_AddNumberToObject(notif, "seer_duration", SEER_PHASE_DURATION);
    cJSON_AddNumberToObject(notif, "guard_duration", GUARD_PHASE_DURATION);
    cJSON_AddNumberToObject(notif, "wolf_duration", WOLF_PHASE_DURATION);
    
    // Thêm players list với đầy đủ thông tin (username, is_alive)
    cJSON *players_array = cJSON_CreateArray();
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        cJSON *player_obj = cJSON_CreateObject();
        cJSON_AddStringToObject(player_obj, "username", rooms[room_index].players[i].username);
        cJSON_AddNumberToObject(player_obj, "is_alive", rooms[room_index].players[i].is_alive);
        cJSON_AddItemToArray(players_array, player_obj);
    }
    cJSON_AddItemToObject(notif, "players", players_array);
    
    char *notif_str = cJSON_PrintUnformatted(notif);
    printf("[SERVER] Broadcasting PHASE_NIGHT (303) to %d players in room %d: %s\n", 
           rooms[room_index].current_players, rooms[room_index].id, notif_str);
    broadcast_room(room_index, PHASE_NIGHT, notif_str);
    free(notif_str);
    cJSON_Delete(notif);
}

int get_user_room(int socket) {
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id != 0) {
            for (int j = 0; j < rooms[i].current_players; j++) {
                if (rooms[i].players[j].socket == socket) {
                    return i;
                }
            }
        }
    }
    return -1;
}

void broadcast_room(int room_index, int header, const char *payload) {
    int sent_count = 0;
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        int sock = rooms[room_index].players[i].socket;
        if (sock > 0){
            send_packet(sock, header, payload);
            sent_count++;
            printf("[SERVER] Sent packet header %d to socket %d (player: %s)\n", 
                   header, sock, rooms[room_index].players[i].username);
        }
    }
    printf("[SERVER] Broadcasted header %d to %d/%d players in room %d\n", 
           header, sent_count, rooms[room_index].current_players, rooms[room_index].id);
}

void cleanup_empty_rooms() {
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id != 0 && rooms[i].current_players == 0) {
            printf("Cleaning up empty room %d ('%s')\n", rooms[i].id, rooms[i].name);
            rooms[i].id = 0;
            rooms[i].name[0] = '\0';
            rooms[i].status = ROOM_WAITING;
            rooms[i].host_socket = 0;
        }
    }
}

void check_role_card_timeouts() {
    time_t now = time(NULL);
    
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == 0) continue;
        if (rooms[i].status != ROOM_PLAYING) continue;
        if (rooms[i].night_phase_active) continue; // Already started night phase
        if (rooms[i].role_card_total == 0) continue; // Not in role card phase
        
        if (rooms[i].role_card_start_time > 0 && 
            now - rooms[i].role_card_start_time >= 30) {
            // Timeout: bắt đầu night phase (duration sẽ được tính từ các phase duration)
            printf("Role card timeout for room %d, starting night phase\n", rooms[i].id);
            start_night_phase(i, 0);  // Parameter không dùng nữa, nhưng giữ để backward compatible
        }
    }
}

void check_seer_phase_timeout() {
    time_t now = time(NULL);
    
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == 0) continue;
        if (rooms[i].status != ROOM_PLAYING) continue;
        if (!rooms[i].night_phase_active) continue; // Not in night phase
        if (rooms[i].seer_choice_made) continue; // Seer already made choice
        if (rooms[i].seer_deadline == 0) continue; // No deadline set
        
        // Check if seer deadline has passed
        if (now >= rooms[i].seer_deadline) {
            printf("[SERVER] Seer phase timeout for room %d, broadcasting PHASE_GUARD_START\n", rooms[i].id);
            rooms[i].seer_choice_made = 1; // Mark as done to prevent multiple broadcasts
            
            // Broadcast guard phase start to all players
            cJSON *guard_notif = cJSON_CreateObject();
            cJSON_AddStringToObject(guard_notif, "type", "phase_guard_start");
            cJSON_AddNumberToObject(guard_notif, "guard_duration", GUARD_PHASE_DURATION);
            char *guard_notif_str = cJSON_PrintUnformatted(guard_notif);
            broadcast_room(i, PHASE_GUARD_START, guard_notif_str);
            free(guard_notif_str);
            cJSON_Delete(guard_notif);
        }
    }
}

void check_guard_phase_timeout() {
    time_t now = time(NULL);
    
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == 0) continue;
        if (rooms[i].status != ROOM_PLAYING) continue;
        if (!rooms[i].night_phase_active) continue; // Not in night phase
        if (!rooms[i].seer_choice_made) continue; // Seer phase not finished yet
        if (rooms[i].guard_choice_made) continue; // Guard already made choice
        if (rooms[i].guard_deadline == 0) continue; // No deadline set
        
        // Check if guard deadline has passed
        if (now >= rooms[i].guard_deadline) {
            printf("[SERVER] Guard phase timeout for room %d, broadcasting PHASE_WOLF_START\n", rooms[i].id);
            rooms[i].guard_choice_made = 1; // Mark as done to prevent multiple broadcasts
            
            // Broadcast wolf phase start to all players
            cJSON *wolf_notif = cJSON_CreateObject();
            cJSON_AddStringToObject(wolf_notif, "type", "phase_wolf_start");
            cJSON_AddNumberToObject(wolf_notif, "wolf_duration", WOLF_PHASE_DURATION);
            char *wolf_notif_str = cJSON_PrintUnformatted(wolf_notif);
            broadcast_room(i, PHASE_WOLF_START, wolf_notif_str);
            free(wolf_notif_str);
            cJSON_Delete(wolf_notif);
        }
    }
}

void check_wolf_phase_timeout() {
    time_t now = time(NULL);
    
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == 0) continue;
        if (rooms[i].status != ROOM_PLAYING) continue;
        if (!rooms[i].night_phase_active) continue; // Not in night phase
        if (!rooms[i].seer_choice_made) continue; // Seer phase not finished yet
        if (!rooms[i].guard_choice_made) continue; // Guard phase not finished yet
        if (rooms[i].wolf_deadline == 0) continue; // No deadline set
        
        // Check if wolf deadline has passed
        if (now >= rooms[i].wolf_deadline) {
            printf("[SERVER] Wolf phase timeout for room %d\n", rooms[i].id);
            
            // Nếu chưa xử lý votes, xử lý votes hiện có (nếu có wolves đã vote)
            if (!rooms[i].wolf_kill_done) {
                int n = rooms[i].current_players;
                
                // Đếm số sói còn sống
                int alive_wolves = 0;
                for (int j = 0; j < n; j++) {
                    if (rooms[i].players[j].role == ROLE_WEREWOLF && rooms[i].players[j].is_alive)
                        alive_wolves++;
                }
                
                // Đếm số sói đã vote
                int wolf_vote_count = 0;
                for (int j = 0; j < n; j++) {
                    if (rooms[i].players[j].role == ROLE_WEREWOLF && rooms[i].players[j].is_alive && 
                        strlen(rooms[i].wolf_votes[j]) > 0)
                        wolf_vote_count++;
                }
                
                // Nếu có ít nhất 1 sói đã vote, xử lý votes
                if (wolf_vote_count > 0) {
                    printf("[SERVER] Processing wolf votes: %d/%d wolves voted\n", wolf_vote_count, alive_wolves);
                    
                    // Đếm số vote cho từng username
                    int vote_tally[MAX_PLAYERS_PER_ROOM] = {0};
                    for (int j = 0; j < n; j++) {
                        if (rooms[i].players[j].role == ROLE_WEREWOLF && rooms[i].players[j].is_alive) {
                            char *voted_name = rooms[i].wolf_votes[j];
                            if (strlen(voted_name) > 0) {
                                for (int k = 0; k < n; k++) {
                                    if (strcmp(rooms[i].players[k].username, voted_name) == 0) {
                                        vote_tally[k]++;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                    
                    // Tìm người bị vote nhiều nhất
                    int max_votes = 0, victim_index = -1;
                    for (int j = 0; j < n; j++) {
                        if (vote_tally[j] > max_votes) {
                            max_votes = vote_tally[j];
                            victim_index = j;
                        }
                    }
                    
                    // Kiểm tra hợp lệ và xử lý kill
                    if (victim_index != -1 && max_votes > 0) {
                        Player *victim = &rooms[i].players[victim_index];
                        // Kiểm tra đã chết chưa
                        if (victim->is_alive) {
                            // Kiểm tra có được bảo vệ không
                            if (strlen(rooms[i].guard_protected_username) > 0 &&
                                strcmp(victim->username, rooms[i].guard_protected_username) == 0) {
                                // Được bảo vệ, không chết
                                printf("[SERVER] %s was protected by guard, survived the attack\n", victim->username);
                            } else {
                                // Không được bảo vệ, set chết
                                victim->is_alive = 0;
                                printf("[SERVER] %s was killed by wolves (votes: %d)\n", victim->username, max_votes);
                            }
                        }
                    } else {
                        printf("[SERVER] No valid victim from wolf votes\n");
                    }
                } else {
                    printf("[SERVER] No wolves voted, no one is killed\n");
                }
                
                rooms[i].wolf_kill_done = 1;
            }
            
            // Kết thúc night phase và chuyển sang day phase
            rooms[i].night_phase_active = 0;
            
            // Collect danh sách người chết (bao gồm cả disconnected users)
            cJSON *dead_players = cJSON_CreateArray();
            for (int j = 0; j < rooms[i].current_players; j++) {
                if (!rooms[i].players[j].is_alive) {
                    cJSON_AddItemToArray(dead_players, cJSON_CreateString(rooms[i].players[j].username));
                    printf("[SERVER] Player %s is dead (included in death list)\n", rooms[i].players[j].username);
                }
            }
            
            // Broadcast day phase start to all players (KHÔNG disconnect/kick ai cả)
            cJSON *day_notif = cJSON_CreateObject();
            cJSON_AddStringToObject(day_notif, "type", "phase_day");
            cJSON_AddStringToObject(day_notif, "message", "Night phase ended, day phase begins");
            cJSON_AddItemToObject(day_notif, "dead_players", dead_players);
            char *day_notif_str = cJSON_PrintUnformatted(day_notif);
            printf("[SERVER] Broadcasting PHASE_DAY (304) to all players in room %d with %d dead players\n", 
                   rooms[i].id, cJSON_GetArraySize(dead_players));
            broadcast_room(i, PHASE_DAY, day_notif_str);
            free(day_notif_str);
            cJSON_Delete(day_notif);
        }
    }
}