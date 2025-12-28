#ifndef ROOM_MANAGER_H
#define ROOM_MANAGER_H

#include "types.h"

void init_rooms();
int get_user_room(int socket);
void broadcast_room(int room_index, int header, const char *payload);
void cleanup_empty_rooms();
// Start night phase for a room (sets deadlines and notifies players)
void start_night_phase(int room_index, int duration_seconds);
// Check role card timeout (30s) and start night phase if needed
void check_role_card_timeouts();

#endif