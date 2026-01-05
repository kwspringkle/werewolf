#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "room_manager.h"
#include "session_manager.h"
#include "packet_handler.h"
#include "cJSON.h"
#include "protocol.h"
#include <time.h>

Room rooms[MAX_ROOMS];

void delete_room(int room_index) {
    if (room_index < 0 || room_index >= MAX_ROOMS) return;

    // Clear players
    for (int i = 0; i < MAX_PLAYERS_PER_ROOM; i++) {
        rooms[room_index].players[i].socket = 0;
        rooms[room_index].players[i].user_id = 0;
        rooms[room_index].players[i].username[0] = '\0';
        rooms[room_index].players[i].role = 0;
        rooms[room_index].players[i].is_alive = 0;
        rooms[room_index].wolf_votes[i][0] = '\0';
    }

    rooms[room_index].id = 0;
    rooms[room_index].name[0] = '\0';
    rooms[room_index].current_players = 0;
    rooms[room_index].status = ROOM_WAITING;
    rooms[room_index].host_socket = 0;

    // Reset night-phase state
    rooms[room_index].night_phase_active = 0;
    rooms[room_index].seer_deadline = 0;
    rooms[room_index].guard_deadline = 0;
    rooms[room_index].wolf_deadline = 0;
    rooms[room_index].seer_choice_made = 0;
    rooms[room_index].seer_chosen_target[0] = '\0';
    rooms[room_index].guard_choice_made = 0;
    rooms[room_index].guard_protected_username[0] = '\0';
    rooms[room_index].wolf_vote_count = 0;
    rooms[room_index].wolf_kill_done = 0;

    // Reset role-card phase
    rooms[room_index].role_card_done_count = 0;
    rooms[room_index].role_card_total = 0;
    rooms[room_index].role_card_start_time = 0;

    // Reset day-phase state
    rooms[room_index].day_phase_active = 0;
    rooms[room_index].day_round = 0;
    rooms[room_index].day_deadline = 0;
    rooms[room_index].day_candidate_count = 0;
    for (int i = 0; i < MAX_PLAYERS_PER_ROOM; i++) {
        rooms[room_index].day_votes[i][0] = '\0';
        rooms[room_index].day_vote_responded[i] = 0;
        rooms[room_index].day_candidate_indices[i] = -1;
    }
}

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

        rooms[i].day_phase_active = 0;
        rooms[i].day_round = 0;
        rooms[i].day_deadline = 0;
        rooms[i].day_candidate_count = 0;
        for (int j = 0; j < MAX_PLAYERS_PER_ROOM; j++) {
            rooms[i].day_votes[j][0] = '\0';
            rooms[i].day_vote_responded[j] = 0;
            rooms[i].day_candidate_indices[j] = -1;
        }
    }
}

static int is_candidate_in_round2(Room *room, int player_index) {
    if (!room || room->day_round != 2) return 1;
    for (int i = 0; i < room->day_candidate_count; i++) {
        if (room->day_candidate_indices[i] == player_index) return 1;
    }
    return 0;
}

static void broadcast_game_over_with_reveal(int room_index, const char *winner_team) {
    cJSON *obj = cJSON_CreateObject();
    cJSON_AddStringToObject(obj, "type", "game_over");
    cJSON_AddStringToObject(obj, "winner", winner_team);

    cJSON *players = cJSON_CreateArray();
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (rooms[room_index].players[i].username[0] == '\0') continue;
        cJSON *p = cJSON_CreateObject();
        cJSON_AddStringToObject(p, "username", rooms[room_index].players[i].username);
        cJSON_AddNumberToObject(p, "role", rooms[room_index].players[i].role);
        cJSON_AddNumberToObject(p, "is_alive", rooms[room_index].players[i].is_alive);
        cJSON_AddItemToArray(players, p);
    }
    cJSON_AddItemToObject(obj, "players", players);

    char *s = cJSON_PrintUnformatted(obj);
    broadcast_room(room_index, GAME_OVER, s);
    free(s);
    cJSON_Delete(obj);
}

void start_day_phase(int room_index) {
    if (room_index < 0 || room_index >= MAX_ROOMS) return;
    if (rooms[room_index].id == 0) return;
    if (rooms[room_index].status != ROOM_PLAYING) return;

    time_t now = time(NULL);
    rooms[room_index].day_phase_active = 1;
    rooms[room_index].day_round = 1;
    rooms[room_index].day_deadline = now + DAY_PHASE_DURATION;
    rooms[room_index].day_candidate_count = 0;
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        rooms[room_index].day_votes[i][0] = '\0';
        rooms[room_index].day_vote_responded[i] = 0;
    }
}

static int _alive_voter_count(int room_index) {
    int n = rooms[room_index].current_players;
    int alive = 0;
    for (int i = 0; i < n; i++) {
        if (rooms[room_index].players[i].username[0] == '\0') continue;
        if (rooms[room_index].players[i].is_alive) alive++;
    }
    return alive;
}

static int _responded_alive_count(int room_index) {
    int n = rooms[room_index].current_players;
    int responded = 0;
    for (int i = 0; i < n; i++) {
        if (rooms[room_index].players[i].username[0] == '\0') continue;
        if (!rooms[room_index].players[i].is_alive) continue;
        if (rooms[room_index].day_vote_responded[i]) responded++;
    }
    return responded;
}

static void execute_player(int room_index, int target_index) {
    if (room_index < 0 || room_index >= MAX_ROOMS) return;
    if (target_index < 0 || target_index >= rooms[room_index].current_players) return;

    rooms[room_index].players[target_index].is_alive = 0;

    cJSON *ev = cJSON_CreateObject();
    cJSON_AddStringToObject(ev, "type", "player_executed");
    cJSON_AddStringToObject(ev, "playerId", rooms[room_index].players[target_index].username);
    char *s = cJSON_PrintUnformatted(ev);
    broadcast_room(room_index, VOTE_RESULT, s);
    free(s);
    cJSON_Delete(ev);
}

int check_win_and_maybe_end(int room_index) {
    int wolves_alive = 0;
    int others_alive = 0;

    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (rooms[room_index].players[i].username[0] == '\0') continue;
        if (!rooms[room_index].players[i].is_alive) continue;
        if (rooms[room_index].players[i].role == ROLE_WEREWOLF) wolves_alive++;
        else others_alive++;
    }

    if (wolves_alive == 0) {
        rooms[room_index].status = ROOM_FINISHED;
        rooms[room_index].day_phase_active = 0;
        rooms[room_index].night_phase_active = 0;
        broadcast_game_over_with_reveal(room_index, "villagers");
        // After announcing final result, delete the room.
        delete_room(room_index);
        return 1;
    }

    if (wolves_alive >= others_alive) {
        rooms[room_index].status = ROOM_FINISHED;
        rooms[room_index].day_phase_active = 0;
        rooms[room_index].night_phase_active = 0;
        broadcast_game_over_with_reveal(room_index, "werewolves");
        // After announcing final result, delete the room.
        delete_room(room_index);
        return 1;
    }

    return 0;
}

static void start_tie_break_round2(int room_index, int *candidates, int candidate_count) {
    time_t now = time(NULL);
    rooms[room_index].day_round = 2;
    rooms[room_index].day_deadline = now + DAY_TIE_BREAK_DURATION;
    rooms[room_index].day_candidate_count = candidate_count;
    for (int i = 0; i < candidate_count; i++) {
        rooms[room_index].day_candidate_indices[i] = candidates[i];
    }
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        rooms[room_index].day_votes[i][0] = '\0';
        rooms[room_index].day_vote_responded[i] = 0;
    }

    cJSON *ev = cJSON_CreateObject();
    cJSON_AddStringToObject(ev, "type", "tie_break_start");
    cJSON *arr = cJSON_CreateArray();
    for (int i = 0; i < candidate_count; i++) {
        int idx = candidates[i];
        if (idx >= 0 && idx < rooms[room_index].current_players) {
            cJSON_AddItemToArray(arr, cJSON_CreateString(rooms[room_index].players[idx].username));
        }
    }
    cJSON_AddItemToObject(ev, "candidates", arr);
    cJSON_AddNumberToObject(ev, "timer", DAY_TIE_BREAK_DURATION);
    cJSON_AddNumberToObject(ev, "deadline", (double)rooms[room_index].day_deadline);
    char *s = cJSON_PrintUnformatted(ev);
    broadcast_room(room_index, VOTE_RESULT, s);
    free(s);
    cJSON_Delete(ev);
}

static void finalize_day_votes(int room_index) {
    int n = rooms[room_index].current_players;
    int tally[MAX_PLAYERS_PER_ROOM] = {0};

    for (int i = 0; i < n; i++) {
        if (rooms[room_index].players[i].username[0] == '\0') continue;
        if (!rooms[room_index].players[i].is_alive) continue; // dead can't vote
        if (rooms[room_index].day_votes[i][0] == '\0') continue; // AFK/null vote

        // Find target index
        for (int j = 0; j < n; j++) {
            if (rooms[room_index].players[j].username[0] == '\0') continue;
            if (!rooms[room_index].players[j].is_alive) continue;
            if (!is_candidate_in_round2(&rooms[room_index], j)) continue;
            if (strcmp(rooms[room_index].players[j].username, rooms[room_index].day_votes[i]) == 0) {
                tally[j]++;
                break;
            }
        }
    }

    int max_votes = 0;
    int candidates[MAX_PLAYERS_PER_ROOM];
    int candidate_count = 0;

    for (int i = 0; i < n; i++) {
        if (tally[i] > max_votes) {
            max_votes = tally[i];
            candidate_count = 0;
            candidates[candidate_count++] = i;
        } else if (tally[i] == max_votes && max_votes > 0) {
            candidates[candidate_count++] = i;
        }
    }

    // No votes => no execution, proceed to night
    if (max_votes == 0 || candidate_count == 0) {
        rooms[room_index].day_phase_active = 0;
        rooms[room_index].day_round = 0;
        rooms[room_index].day_candidate_count = 0;
        start_night_phase(room_index, 0);
        return;
    }

    if (candidate_count == 1) {
        execute_player(room_index, candidates[0]);
        rooms[room_index].day_phase_active = 0;
        rooms[room_index].day_round = 0;
        rooms[room_index].day_candidate_count = 0;

        if (!check_win_and_maybe_end(room_index)) {
            start_night_phase(room_index, 0);
        }
        return;
    }

    if (rooms[room_index].day_round == 1) {
        start_tie_break_round2(room_index, candidates, candidate_count);
        return;
    }

    // Round 2 tie => random select among tied candidates
    srand((unsigned int)time(NULL) + room_index);
    int selected_index = candidates[rand() % candidate_count];

    cJSON *ev = cJSON_CreateObject();
    cJSON_AddStringToObject(ev, "type", "execution_random_selected");
    cJSON *arr = cJSON_CreateArray();
    for (int i = 0; i < candidate_count; i++) {
        int idx = candidates[i];
        cJSON_AddItemToArray(arr, cJSON_CreateString(rooms[room_index].players[idx].username));
    }
    cJSON_AddItemToObject(ev, "candidates", arr);
    cJSON_AddStringToObject(ev, "selected", rooms[room_index].players[selected_index].username);
    cJSON_AddStringToObject(ev, "reason", "tie_break_still_equal");
    char *s = cJSON_PrintUnformatted(ev);
    broadcast_room(room_index, VOTE_RESULT, s);
    free(s);
    cJSON_Delete(ev);

    execute_player(room_index, selected_index);
    rooms[room_index].day_phase_active = 0;
    rooms[room_index].day_round = 0;
    rooms[room_index].day_candidate_count = 0;

    if (!check_win_and_maybe_end(room_index)) {
        start_night_phase(room_index, 0);
    }
}

void maybe_finalize_day_votes_early(int room_index) {
    if (room_index < 0 || room_index >= MAX_ROOMS) return;
    if (rooms[room_index].id == 0) return;
    if (rooms[room_index].status != ROOM_PLAYING) return;
    if (!rooms[room_index].day_phase_active) return;

    int alive = _alive_voter_count(room_index);
    if (alive <= 0) return;

    int responded = _responded_alive_count(room_index);
    if (responded >= alive) {
        printf("[SERVER] All alive players responded in room %d (round %d). Finalizing votes early.\n",
               rooms[room_index].id, rooms[room_index].day_round);
        finalize_day_votes(room_index);
    }
}

void check_day_phase_timeout() {
    time_t now = time(NULL);
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == 0) continue;
        if (rooms[i].status != ROOM_PLAYING) continue;
        if (!rooms[i].day_phase_active) continue;
        if (rooms[i].day_deadline == 0) continue;

        if (now >= rooms[i].day_deadline) {
            printf("[SERVER] Day phase timeout in room %d (round %d). Finalizing votes.\n", rooms[i].id, rooms[i].day_round);
            finalize_day_votes(i);
        }
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
        rooms[room_index].wolf_vote_responded[i] = 0;
    }

    cJSON *notif = cJSON_CreateObject();
    cJSON_AddStringToObject(notif, "type", "phase_night");
    cJSON_AddNumberToObject(notif, "duration", total_duration);
    cJSON_AddNumberToObject(notif, "seer_duration", SEER_PHASE_DURATION);
    cJSON_AddNumberToObject(notif, "guard_duration", GUARD_PHASE_DURATION);
    cJSON_AddNumberToObject(notif, "wolf_duration", WOLF_PHASE_DURATION);
    
    // Thêm players list với đầy đủ thông tin (username, is_alive, role)
    cJSON *players_array = cJSON_CreateArray();
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        cJSON *player_obj = cJSON_CreateObject();
        cJSON_AddStringToObject(player_obj, "username", rooms[room_index].players[i].username);
        cJSON_AddNumberToObject(player_obj, "is_alive", rooms[room_index].players[i].is_alive);
        cJSON_AddNumberToObject(player_obj, "role", rooms[room_index].players[i].role);
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
        if (rooms[i].id == 0) continue;

        // Legacy cleanup: no players
        if (rooms[i].current_players == 0) {
            printf("Cleaning up empty room %d ('%s')\n", rooms[i].id, rooms[i].name);
            delete_room(i);
            continue;
        }

        // Check if all players are disconnected (socket == 0)
        int connected_count = 0;
        for (int j = 0; j < rooms[i].current_players; j++) {
            if (rooms[i].players[j].username[0] == '\0') continue;
            if (rooms[i].players[j].socket > 0) connected_count++;
        }
        
        // If all players disconnected, delete room
        if (connected_count == 0) {
            printf("Cleaning up room %d ('%s') - all players disconnected\n", rooms[i].id, rooms[i].name);
            delete_room(i);
            continue;
        }

        // New cleanup: game running but everyone is dead/disconnected.
        if (rooms[i].status == ROOM_PLAYING) {
            int alive_count = 0;
            for (int j = 0; j < rooms[i].current_players; j++) {
                if (rooms[i].players[j].username[0] == '\0') continue;
                if (rooms[i].players[j].is_alive) alive_count++;
            }
            if (alive_count == 0) {
                printf("Cleaning up dead room %d ('%s') - all players are dead/disconnected\n", rooms[i].id, rooms[i].name);
                delete_room(i);
            }
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
                const char *result = "no_kill";
                const char *target_id = NULL;
                
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
                    
                    // Tìm người bị vote nhiều nhất (với tie-breaking)
                    int max_votes = 0;
                    int victim_candidates[MAX_PLAYERS_PER_ROOM];
                    int candidate_count = 0;
                    
                    for (int j = 0; j < n; j++) {
                        if (vote_tally[j] > max_votes) {
                            max_votes = vote_tally[j];
                            candidate_count = 0;
                            victim_candidates[candidate_count++] = j;
                        } else if (vote_tally[j] == max_votes && max_votes > 0) {
                            victim_candidates[candidate_count++] = j;
                        }
                    }
                    
                    // Xử lý kết quả vote
                    int victim_index = -1;
                    
                    if (candidate_count > 0 && max_votes > 0) {
                        // Nếu hòa (nhiều người cùng số vote cao nhất), random chọn 1
                        if (candidate_count > 1) {
                            srand((unsigned int)time(NULL) + i); // Seed với time + room để đảm bảo random
                            victim_index = victim_candidates[rand() % candidate_count];
                            printf("[SERVER] Tie detected (%d candidates), randomly selected: %s\n", 
                                   candidate_count, rooms[i].players[victim_index].username);
                        } else {
                            victim_index = victim_candidates[0];
                        }
                        
                        Player *victim = &rooms[i].players[victim_index];
                        target_id = victim->username;
                        
                        // Kiểm tra đã chết chưa
                        if (victim->is_alive) {
                            // Kiểm tra có được bảo vệ không
                            if (strlen(rooms[i].guard_protected_username) > 0 &&
                                strcmp(victim->username, rooms[i].guard_protected_username) == 0) {
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
                } else {
                    printf("[SERVER] No wolves voted, no one is killed\n");
                }
                
                rooms[i].wolf_kill_done = 1;
            
                // Kết thúc night phase
            rooms[i].night_phase_active = 0;

                // Start day phase voting/discussion (round 1)
                start_day_phase(i);
            
                // Gửi compact result thay vì large dead_players array
                cJSON *result_obj = cJSON_CreateObject();
                cJSON_AddStringToObject(result_obj, "type", "phase_day");
                cJSON_AddStringToObject(result_obj, "result", result);
                if (target_id != NULL && strcmp(result, "killed") == 0) {
                    cJSON_AddStringToObject(result_obj, "targetId", target_id);
                }
                cJSON_AddNumberToObject(result_obj, "day_duration", DAY_PHASE_DURATION);
                cJSON_AddNumberToObject(result_obj, "day_deadline", (double)rooms[i].day_deadline);
                char *result_str = cJSON_PrintUnformatted(result_obj);
                printf("[SERVER] Wolf phase timeout in room %d, broadcasting compact PHASE_DAY (304): result=%s%s%s\n", 
                       rooms[i].id, result,
                       (target_id && strcmp(result, "killed") == 0) ? ", target=" : "",
                       (target_id && strcmp(result, "killed") == 0) ? target_id : "");
                broadcast_room(i, PHASE_DAY, result_str);
                free(result_str);
                cJSON_Delete(result_obj);
            } else {
                // Kết thúc night phase (đã xử lý trước đó)
                rooms[i].night_phase_active = 0;
            }
        }
    }
}