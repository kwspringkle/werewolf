#include <stdio.h>
#include <sys/socket.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <time.h>
#include <stdint.h>

#include "database.h"
#include "room_manager.h"
#include "session_manager.h"
#include "packet_handler.h"

int main() {
    load_env();
    connect_db();
    init_rooms();
    init_sessions();

    int server_fd, new_socket, clients[30];
    struct sockaddr_in address;
    fd_set readfds;

    for (int i = 0; i < 30; i++) clients[i] = 0;

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    int opt = 1;
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("Setsockopt failed");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) {
        perror("Bind failed");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 10) < 0) {
        perror("Listen failed");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    printf("SERVER RUNNING ON PORT %d...\n", PORT);

    time_t last_check = time(NULL);
    time_t last_cleanup = time(NULL);

    while (1) {
        struct timeval tv = {5, 0};

        FD_ZERO(&readfds);
        FD_SET(server_fd, &readfds);
        int max_sd = server_fd;

        for (int i = 0; i < 30; i++) {
            int sd = clients[i];
            if (sd > 0) FD_SET(sd, &readfds);
            if (sd > max_sd) max_sd = sd;
        }

        select(max_sd + 1, &readfds, NULL, NULL, NULL);

        // new client
        if (FD_ISSET(server_fd, &readfds)) {
            int addrlen = sizeof(address);
            new_socket = accept(server_fd, (struct sockaddr*)&address, (socklen_t*)&addrlen);

            char client_ip[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &address.sin_addr, client_ip, INET_ADDRSTRLEN);
            printf("Client connected: socket=%d from %s:%d\n", 
                new_socket, client_ip, ntohs(address.sin_port));


            for (int i = 0; i < 30; i++) {
                if (clients[i] == 0) {
                    clients[i] = new_socket;
                    break;
                }
            }
        }

        // handle client
        for (int i = 0; i < 30; i++) {
            int sd = clients[i];
            if (sd <= 0) continue;

            if (FD_ISSET(sd, &readfds)) {

                uint16_t header_buf;
                int b = recv(sd, &header_buf, 2, MSG_WAITALL);
                if (b <= 0) {
                    handle_disconnect(sd);
                    close(sd);
                    clients[i] = 0;
                    continue;
                }

                uint32_t len_buf;
                recv(sd, &len_buf, 4, MSG_WAITALL);

                uint16_t header = ntohs(header_buf);
                uint32_t length = ntohl(len_buf);

                if (length > 65536) {
                    printf("Payload too large from client %d, disconnecting\n", sd);
                    handle_disconnect(sd);
                    close(sd);
                    clients[i] = 0;
                    continue;
                }

                char *payload = malloc(length + 1);
                if (!payload) {
                    fprintf(stderr, "Failed to allocate memory for payload\n");
                    handle_disconnect(sd);
                    close(sd);
                    clients[i] = 0;
                    continue;
                }

                recv(sd, payload, length, MSG_WAITALL);
                payload[length] = '\0';

                printf("[Client %d] Header=%d Payload=%s\n", sd, header, payload);

                process_packet(sd, header, payload);

                free(payload);
            }
        }

        time_t now = time(NULL);
        if (now - last_check >= 10) {
            send_ping_to_all_clients();
            check_timeouts();
            last_check = now;
        }

        if (now - last_cleanup >= 60) {
            cleanup_empty_rooms();
            last_cleanup = now;
        }
    }

    mysql_close(conn);
    return 0;
}