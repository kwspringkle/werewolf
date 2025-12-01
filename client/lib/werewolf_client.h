#ifndef WEREWOLF_CLIENT_H
#define WEREWOLF_CLIENT_H

#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>

typedef int socket_t;
#define INVALID_SOCKET_VALUE -1
#define SOCKET_ERROR_VALUE -1
#define closesocket close

typedef struct {
    socket_t sock;
    int is_connected;
    char last_error[256];
} WerewolfClient;

WerewolfClient* ww_client_create();
int ww_client_connect(WerewolfClient* client, const char* host, int port);
int ww_client_send(WerewolfClient* client, unsigned short header, const char* json);
int ww_client_receive(WerewolfClient* client, unsigned short* out_header,
                      char* out_payload, int max_size);
void ww_client_disconnect(WerewolfClient* client);
void ww_client_destroy(WerewolfClient* client);
const char* ww_client_get_error(WerewolfClient* client);

#endif
