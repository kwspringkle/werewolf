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