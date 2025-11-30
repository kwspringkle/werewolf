#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "room_manager.h"
#include "session_manager.h"
#include "packet_handler.h"
#include "cJSON.h"

Room rooms[MAX_ROOMS];

void init_rooms() {
    for (int i = 0; i < MAX_ROOMS; i++) {
        rooms[i].id = 0;
        rooms[i].name[0] = '\0';
        rooms[i].current_players = 0;
        rooms[i].status = ROOM_WAITING;
        rooms[i].host_socket = 0;
    }
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
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        int sock = rooms[room_index].players[i].socket;
        if (sock > 0){
            send_packet(sock, header, payload);
        }
    }
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