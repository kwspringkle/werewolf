#ifndef ROOM_MANAGER_H
#define ROOM_MANAGER_H

#include "types.h"

void init_rooms();
int get_user_room(int socket);
void broadcast_room(int room_index, int header, const char *payload);
void cleanup_empty_rooms();
// Start night phase for a room (sets deadlines sequentially: seer -> guard -> wolf)
// duration_seconds parameter is deprecated (kept for backward compatibility)
// Total duration is calculated from SEER_PHASE_DURATION + GUARD_PHASE_DURATION + WOLF_PHASE_DURATION
void start_night_phase(int room_index, int duration_seconds);
// Check role card timeout (30s) and start night phase if needed
void check_role_card_timeouts();
// Check seer phase timeout and broadcast guard phase start
void check_seer_phase_timeout();
// Check guard phase timeout and broadcast wolf phase start
void check_guard_phase_timeout();
// Check wolf phase timeout, process votes if any, and broadcast day phase start
void check_wolf_phase_timeout();

#endif