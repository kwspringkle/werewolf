#ifndef ROOM_MANAGER_H
#define ROOM_MANAGER_H

#include "types.h"

void init_rooms();
int get_user_room(int socket);
void broadcast_room(int room_index, int header, const char *payload);
void cleanup_empty_rooms();

#endif