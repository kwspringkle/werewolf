#include "werewolf_client.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>

// Hàm báo lỗi
static void set_error(WerewolfClient* c, const char* msg) {
    if (c) {
        strncpy(c->last_error, msg, 255);
        c->last_error[255] = 0;
    }
}

// Hàm tạo client mới
WerewolfClient* ww_client_create() {
    WerewolfClient* c = malloc(sizeof(WerewolfClient));
    if (!c) return NULL;

    c->sock = INVALID_SOCKET_VALUE;
    c->is_connected = 0;
    memset(c->last_error, 0, sizeof(c->last_error));
    return c;
}

// Hàm kết nối đến server
int ww_client_connect(WerewolfClient* c, const char* host, int port) {
    if (!c) return -1;

    c->sock = socket(AF_INET, SOCK_STREAM, 0);
    if (c->sock == INVALID_SOCKET_VALUE) {
        set_error(c, "Failed to create socket");
        return -1;
    }

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port   = htons(port);
    if (inet_pton(AF_INET, host, &addr.sin_addr) <= 0) {
        set_error(c, "Invalid IP");
        closesocket(c->sock);
        return -1;
    }

    if (connect(c->sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        set_error(c, "Connect failed");
        closesocket(c->sock);
        return -1;
    }
    c->is_connected = 1;
    return 0;
}

// Hàm gửi dữ liệu
int ww_client_send(WerewolfClient* c, unsigned short header, const char* json) {
    if (!c || !c->is_connected) return -1;

    int plen = json ? strlen(json) : 0;
    int tlen = 6 + plen;
    unsigned char* buf = malloc(tlen);

    buf[0] = header >> 8;
    buf[1] = header & 0xFF;
    buf[2] = (plen >> 24) & 0xFF;
    buf[3] = (plen >> 16) & 0xFF;
    buf[4] = (plen >> 8) & 0xFF;
    buf[5] = plen & 0xFF;

    if (plen > 0) memcpy(buf + 6, json, plen);

    int sent = send(c->sock, buf, tlen, 0);
    free(buf);

    if (sent <= 0) {
        set_error(c, "Send failed");
        return -1;
    }

    return sent;
}

// Hàm nhận dữ liệu
int ww_client_receive(WerewolfClient* c, unsigned short* h, char* out, int max) {
    if (!c || !c->is_connected) return -1;

    unsigned char hdr[2];
    int r = recv(c->sock, hdr, 2, 0);
    if (r <= 0) return 0;

    *h = (hdr[0] << 8) | hdr[1];

    unsigned char lenbuf[4];
    r = recv(c->sock, lenbuf, 4, 0);
    if (r < 4) return 0;

    int len = (lenbuf[0] << 24) | (lenbuf[1] << 16) |
              (lenbuf[2] << 8)  | lenbuf[3];

    if (len >= max) {
        set_error(c, "Payload too large");
        return -1;
    }

    int got = 0;
    while (got < len) {
        r = recv(c->sock, out + got, len - got, 0);
        if (r <= 0) return 0;
        got += r;
    }

    out[len] = 0;
    return *h;
}

// Khi client ngắt kết nối
void ww_client_disconnect(WerewolfClient* c) {
    if (!c) return;
    if (c->sock != INVALID_SOCKET_VALUE) {
        closesocket(c->sock);
        c->sock = INVALID_SOCKET_VALUE;
    }
    c->is_connected = 0;
}

// Hàm hủy client
void ww_client_destroy(WerewolfClient* c) {
    if (!c) return;
    ww_client_disconnect(c);
    free(c);
}

// Lấy lỗi
const char* ww_client_get_error(WerewolfClient* c) {
    return c ? c->last_error : "Invalid client";
}
