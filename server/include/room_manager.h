#ifndef ROOM_MANAGER_H
#define ROOM_MANAGER_H

#include "types.h"

void init_rooms();
int get_user_room(int socket);
void broadcast_room(int room_index, int header, const char *payload);
// Delete and reset a room slot (id becomes 0)
void delete_room(int room_index);
void cleanup_empty_rooms();
// Start night phase for a room (sets deadlines sequentially: seer -> guard -> wolf)
// duration_seconds parameter is deprecated (kept for backward compatibility)
// Total duration is calculated from SEER_PHASE_DURATION + GUARD_PHASE_DURATION + WOLF_PHASE_DURATION
void start_night_phase(int room_index, int duration_seconds);
// Start day phase voting (round 1) for a room
void start_day_phase(int room_index);
// If all alive players have responded (vote or skip), finalize immediately.
void maybe_finalize_day_votes_early(int room_index);
// Check role card timeout (30s) and start night phase if needed
void check_role_card_timeouts();
// Check seer phase timeout and broadcast guard phase start
void check_seer_phase_timeout();
// Check guard phase timeout and broadcast wolf phase start
void check_guard_phase_timeout();
// Check wolf phase timeout, process votes if any, and broadcast day phase start
void check_wolf_phase_timeout();
// Check day phase timeout, process votes, execute, and proceed to night or game over
void check_day_phase_timeout();
// Check win condition and end game if needed (returns 1 if game ended, 0 otherwise)
int check_win_and_maybe_end(int room_index);
// Check disconnected players timeout (2 phút) và đánh chết nếu quá hạn
void check_disconnect_timeouts();

#endif