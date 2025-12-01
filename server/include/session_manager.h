#ifndef SESSION_MANAGER_H
#define SESSION_MANAGER_H

#include "types.h"
#include "protocol.h"
#include "cJSON.h" 

void init_sessions();
Session* find_session(int socket);
void add_session(int socket, int user_id, const char *username);
void remove_session(int socket);
void send_ping_to_all_clients();
void check_timeouts();

#endif