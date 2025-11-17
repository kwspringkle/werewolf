#include <stdio.h>
#include <sys/socket.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

#define PORT 5000

void send_packet(int client_fd, uint16_t header, const char *payload) {
    uint32_t len = strlen(payload);

    uint16_t h = htons(header);
    uint32_t l = htonl(len);

    char *buffer = malloc(6 + len);

    memcpy(buffer,     &h, 2);
    memcpy(buffer + 2, &l, 4);
    memcpy(buffer + 6, payload, len);

    send(client_fd, buffer, 6 + len, 0);

    free(buffer);
}

int main() {
    int server_fd, new_socket, clients[30];
    struct sockaddr_in address;
    fd_set readfds;

    for (int i = 0; i < 30; i++) clients[i] = 0;

    server_fd = socket(AF_INET, SOCK_STREAM, 0);

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    bind(server_fd, (struct sockaddr*)&address, sizeof(address));
    listen(server_fd, 10);

    printf("SERVER RUNNING ON PORT %d...\n", PORT);

    while (1) {
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

            printf("Client connected: %d\n", new_socket);

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
                    printf("Client %d disconnected\n", sd);
                    close(sd);
                    clients[i] = 0;
                    continue;
                }

                uint32_t len_buf;
                recv(sd, &len_buf, 4, MSG_WAITALL);

                uint16_t header = ntohs(header_buf);
                uint32_t length = ntohl(len_buf);

                char *payload = malloc(length + 1);
                recv(sd, payload, length, MSG_WAITALL);
                payload[length] = '\0';

                printf("[Client %d] Header=%d Payload=%s\n", sd, header, payload);

                // create response JSON
                char response[2048];
                snprintf(response, sizeof(response),
                         "{\"server_received\":true,\"your_header\":%d,\"payload\":%s}",
                         header, payload);

                send_packet(sd, header + 100, response);

                free(payload);
            }
        }
    }

    return 0;
}
