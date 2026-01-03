#include "werewolf_client.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#include <sys/select.h>
#include <time.h>
#include "../../server/include/protocol.h"

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
    c->rbuf = NULL;
    c->rbuf_len = 0;
    c->rbuf_cap = 0;
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
    int flags = fcntl(c->sock, F_GETFL, 0);
    if (flags >= 0) fcntl(c->sock, F_SETFL, flags | O_NONBLOCK);
    
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

    // Gửi tất cả dữ liệu ngay cả khi ở chế độ non-blocking
    int total_sent = 0;
    while (total_sent < tlen) {
        int sent = send(c->sock, buf + total_sent, tlen - total_sent, 0);
        if (sent < 0) {
            if (errno == EWOULDBLOCK || errno == EAGAIN) {
                // Đợi rồi thử lại
                continue;
            }
            set_error(c, "Send failed");
            free(buf);
            return -1;
        }
        total_sent += sent;
    }
    
    free(buf);
    return total_sent;
}

// Hàm nhận dữ liệu (non-blocking)
static int ensure_capacity(WerewolfClient* c, size_t need) {
    if (need <= c->rbuf_cap) return 1;
    size_t new_cap = c->rbuf_cap ? c->rbuf_cap : 8192;
    while (new_cap < need) new_cap *= 2;
    unsigned char* nb = realloc(c->rbuf, new_cap);
    if (!nb) return 0;
    c->rbuf = nb;
    c->rbuf_cap = new_cap;
    return 1;
}

int ww_client_receive(WerewolfClient* c, unsigned short* h, char* out, int max) {
    if (!c || !c->is_connected) return -1;

    // Đọc bất kỳ byte nào có sẵn
    unsigned char tmp[4096];
    int r = recv(c->sock, tmp, sizeof(tmp), 0);
    if (r > 0) {
        if (!ensure_capacity(c, c->rbuf_len + r)) {
            set_error(c, "Buffer alloc failed");
            return -1;
        }
        memcpy(c->rbuf + c->rbuf_len, tmp, r);
        c->rbuf_len += r;
    } else if (r < 0) {
        if (errno != EWOULDBLOCK && errno != EAGAIN) {
            set_error(c, "Recv error");
            return -1;
        }
    } else if (r == 0) {
        set_error(c, "Server closed");
        c->is_connected = 0;
        return -1;
    }

    // Cần ít nhất 6 byte (header + độ dài)
    if (c->rbuf_len < 6) return 0;
    uint16_t header = (uint16_t)((c->rbuf[0] << 8) | c->rbuf[1]);
    uint32_t length = (uint32_t)((c->rbuf[2] << 24) | (c->rbuf[3] << 16) | (c->rbuf[4] << 8) | c->rbuf[5]);
    size_t frame_size = 6 + length;
    if (c->rbuf_len < frame_size) return 0; // đợi thêm dữ liệu
    if ((int)length >= max) {
        set_error(c, "Payload too large");
        return -1;
    }
    memcpy(out, c->rbuf + 6, length);
    out[length] = 0;
    *h = header;
    size_t remaining = c->rbuf_len - frame_size;
    if (remaining > 0) memmove(c->rbuf, c->rbuf + frame_size, remaining);
    c->rbuf_len = remaining;
    return header;
}

int ww_client_player_ready_send(WerewolfClient* c, int is_ready) {
    if (!c || !c->is_connected) return -1;

    char json[256];
    int n = snprintf(json, sizeof(json), "{\"is_ready\":%s}",
                     is_ready ? "true" : "false");
    if (n < 0 || n >= (int)sizeof(json)) {
        set_error(c, "Player ready JSON too large");
        return -1;
    }

    return ww_client_send(c, ROLE_CARD_DONE_REQ, json);
}

int ww_client_seer_check_send(WerewolfClient* c, int room_id, const char* target_username) {
    if (!c || !c->is_connected || !target_username) return -1;

    char json[512];
    // Simple JSON construction; assume target_username does not contain quotes
    int n = snprintf(json, sizeof(json), "{\"room_id\":%d,\"target_username\":\"%s\"}", room_id, target_username);
    if (n < 0 || n >= (int)sizeof(json)) {
        set_error(c, "Seer JSON too large");
        return -1;
    }

    return ww_client_send(c, SEER_CHECK_REQ, json);
}


int ww_client_wait_for_seer_result(WerewolfClient* c, int timeout_seconds, char* out_payload, int max_size) {
    if (!c || !c->is_connected || !out_payload || max_size <= 0) return -1;

    time_t end = time(NULL) + timeout_seconds;
    while (1) {
        unsigned short header = 0;
        int r = ww_client_receive(c, &header, out_payload, max_size);
        if (r < 0) return -1; // error
        if (r > 0) {
            // got a full packet; return its header
            return header;
        }

        // no full packet yet; wait for socket readability until deadline
        time_t now = time(NULL);
        if (now >= end) return 0; // timeout

        fd_set rfds;
        FD_ZERO(&rfds);
        FD_SET(c->sock, &rfds);
        struct timeval tv;
        long rem = end - now;
        tv.tv_sec = rem > 0 ? rem : 0;
        tv.tv_usec = 0;

        int sel = select(c->sock + 1, &rfds, NULL, NULL, &tv);
        if (sel < 0) {
            set_error(c, "select() failed");
            return -1;
        }
        if (sel == 0) {
            return 0; // timeout
        }
        // else socket readable, loop to call ww_client_receive again
    }
}

// Hàm gửi yêu cầu sói cắn (werewolf kill)
int ww_client_wolf_kill_send(WerewolfClient* c, int room_id, const char* target_username) {
    if (!c || !c->is_connected || !target_username) return -1;

    char json[512];
    int n = snprintf(json, sizeof(json), "{\"room_id\":%d,\"target_username\":\"%s\"}", room_id, target_username);
    if (n < 0 || n >= (int)sizeof(json)) {
        set_error(c, "Wolf kill JSON too large");
        return -1;
    }

    return ww_client_send(c, WOLF_KILL_REQ, json);
}
// Hàm gửi bảo vệ (guard protect)
int ww_client_guard_protect_send(WerewolfClient* c, int room_id, const char* target_username) {
    if (!c || !c->is_connected || !target_username) return -1;

    char json[512];
    // Simple JSON construction; assume target_username does not contain quotes
    int n = snprintf(json, sizeof(json), "{\"room_id\":%d,\"target_username\":\"%s\"}", room_id, target_username);
    if (n < 0 || n >= (int)sizeof(json)) {
        set_error(c, "Guard JSON too large");
        return -1;
    }

    return ww_client_send(c, GUARD_PROTECT_REQ, json);
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
    if (c->rbuf) free(c->rbuf);
    free(c);
}

// Lấy lỗi
const char* ww_client_get_error(WerewolfClient* c) {
    return c ? c->last_error : "Invalid client";
}