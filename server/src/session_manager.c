#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "session_manager.h"
#include "packet_handler.h"
#include "types.h"
#include "cJSON.h"

Session sessions[MAX_SESSIONS];

void init_sessions() {
    for (int i = 0; i < MAX_SESSIONS; i++) {
        sessions[i].socket = 0;
        sessions[i].user_id = 0;
        sessions[i].username[0] = '\0';
        sessions[i].is_logged_in = 0;
    }
}

Session* find_session(int socket) {
    for (int i = 0; i < MAX_SESSIONS; i++) {
        if (sessions[i].socket == socket && sessions[i].is_logged_in) {
            return &sessions[i];
        }
    }
    return NULL;
}

void add_session(int socket, int user_id, const char *username) {
    for (int i = 0; i < MAX_SESSIONS; i++) {
        if (sessions[i].socket == 0 || sessions[i].socket == socket) {
            sessions[i].socket = socket;
            sessions[i].user_id = user_id;
            strncpy(sessions[i].username, username, sizeof(sessions[i].username) - 1);
            sessions[i].is_logged_in = 1;
            sessions[i].last_ping = time(NULL);
            printf("Session created: socket=%d, user_id=%d, username=%s\n", socket, user_id, username);
            return;
        }
    }
}

void remove_session(int socket) {
    for (int i = 0; i < MAX_SESSIONS; i++) {
        if (sessions[i].socket == socket) {
            printf("Session removed: socket=%d, username=%s\n", socket, sessions[i].username);
            sessions[i].socket = 0;
            sessions[i].user_id = 0;
            sessions[i].username[0] = '\0';
            sessions[i].is_logged_in = 0;
            return;
        }
    }
}

void send_ping_to_all_clients(){
    time_t now = time(NULL);

    for (int i = 0; i < MAX_SESSIONS; i++) {
        if (sessions[i].is_logged_in){
            if (now - sessions[i].last_ping >= 30) {
                cJSON *ping = cJSON_CreateObject();
                cJSON_AddStringToObject(ping, "type", "ping");
                char *ping_str = cJSON_PrintUnformatted(ping);
                send_packet(sessions[i].socket, PING, ping_str);
                free(ping_str);
                cJSON_Delete(ping);
                sessions[i].last_ping = now;
            }
        }
    }
}

void check_timeouts() {
    time_t now = time(NULL);

    for (int i = 0; i < MAX_SESSIONS; i++) {
        if (sessions[i].is_logged_in){
            if (now - sessions[i].last_ping >= 90) {
                printf("Client %d timed out due to inactivity.\n", sessions[i].socket);
                handle_disconnect(sessions[i].socket);
                close(sessions[i].socket);
            }
        }
    }
}