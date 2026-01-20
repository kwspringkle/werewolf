#include <stdio.h>
#include <sys/socket.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <time.h>
#include <stdint.h>
#include <errno.h>
// Thư viện fcntl để thiết lập socket non-blocking
#include <fcntl.h>

#include "database.h"
#include "room_manager.h"
#include "session_manager.h"
#include "packet_handler.h"

// Buffer state cho mỗi client
typedef struct {
    int sd;
    unsigned char *buf;     // dynamic buffer
    size_t buf_len;          // bytes đang lưu trữ
    size_t buf_cap;          // capacity
    time_t last_active;      // thời điểm nhận gói tin cuối cùng
} ClientState;

// Đặt lại trạng thái client
static void client_reset(ClientState *c) {
    if (!c) return;
    if (c->sd > 0) close(c->sd);
    c->sd = 0;
    if (c->buf) {
        free(c->buf);
        c->buf = NULL;
    }
    c->buf_len = 0;
    c->buf_cap = 0;
    c->last_active = 0;
}

// Mở rộng buffer nếu cần
static int ensure_capacity(ClientState *c, size_t need) {
    if (need <= c->buf_cap) return 1;
    size_t new_cap = c->buf_cap ? c->buf_cap : 8192;
    while (new_cap < need) new_cap *= 2;
    unsigned char *nbuf = realloc(c->buf, new_cap);
    if (!nbuf) return 0;
    c->buf = nbuf;
    c->buf_cap = new_cap;
    return 1;
}

static void process_client_buffer(ClientState *c) {
    // Xử lý tất cả các gói tin trong buffer
    while (c->buf_len >= 6) {
        // Trích xuất header (2 byte) và độ dài (4 byte) theo định dạng big-endian
        uint16_t header = (uint16_t)( (c->buf[0] << 8) | c->buf[1] );
        uint32_t length = (uint32_t)( (c->buf[2] << 24) | (c->buf[3] << 16) | (c->buf[4] << 8) | c->buf[5] );
        if (length > 65536) {
            printf("Payload too large from client %d, disconnecting\n", c->sd);
            handle_disconnect(c->sd);
            client_reset(c);
            return;
        }
        size_t frame_size = 6 + length;
        if (c->buf_len < frame_size) break; // đợi thêm dữ liệu
        // frame đầy đủ: header + payload
        char *payload = malloc(length + 1);
        if (!payload) {
            fprintf(stderr, "Failed to allocate memory for payload (client %d)\n", c->sd);
            handle_disconnect(c->sd);
            client_reset(c);
            return;
        }
        memcpy(payload, c->buf + 6, length);
        payload[length] = '\0';
        printf("[Client %d] Header=%d Payload=%s\n", c->sd, header, payload);
        process_packet(c->sd, header, payload);
        free(payload);
        c->last_active = time(NULL);
        // Xóa frame đã xử lý khỏi buffer
        size_t remaining = c->buf_len - frame_size;
        if (remaining > 0) memmove(c->buf, c->buf + frame_size, remaining);
        c->buf_len = remaining;
    }
}

int main() {
    load_env();
    connect_db();
    init_rooms();
    init_sessions();

    int server_fd, new_socket;
    ClientState clients[30];
    struct sockaddr_in address;
    fd_set readfds;

    for (int i = 0; i < 30; i++) {
        clients[i].sd = 0;
        clients[i].buf = NULL;
        clients[i].buf_len = 0;
        clients[i].buf_cap = 0;
        clients[i].last_active = 0;
    }

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

    // Thiết lập socket lắng nghe ở chế độ non-blocking
    int flags = fcntl(server_fd, F_GETFL, 0);
    if (flags >= 0) fcntl(server_fd, F_SETFL, flags | O_NONBLOCK);

    printf("SERVER RUNNING ON PORT %d...\n", PORT);

    time_t last_check = time(NULL);
    time_t last_cleanup = time(NULL);

    while (1) {
        // Timeout tối đa cho select: 1 giây
        // Đảm bảo vòng lặp main luôn "thức dậy" ít nhất mỗi 1 giây
        // để chạy các hàm check_timeouts(), check_disconnect_timeouts(), cleanup_empty_rooms(), ...
        struct timeval tv = {1, 0};

        FD_ZERO(&readfds);
        FD_SET(server_fd, &readfds);
        int max_sd = server_fd;

        for (int i = 0; i < 30; i++) {
            int sd = clients[i].sd;
            if (sd > 0) {
                FD_SET(sd, &readfds);
                if (sd > max_sd) max_sd = sd;
            }
        }

        int sel = select(max_sd + 1, &readfds, NULL, NULL, &tv);
        if (sel < 0) {
            perror("select failed");
            break;
        }

        // client mới
        if (FD_ISSET(server_fd, &readfds)) {
            int addrlen = sizeof(address);
            new_socket = accept(server_fd, (struct sockaddr*)&address, (socklen_t*)&addrlen);
            if (new_socket >= 0) {
                // Set client socket non-blocking
                int cflags = fcntl(new_socket, F_GETFL, 0);
                if (cflags >= 0) fcntl(new_socket, F_SETFL, cflags | O_NONBLOCK);

                char client_ip[INET_ADDRSTRLEN];
                inet_ntop(AF_INET, &address.sin_addr, client_ip, INET_ADDRSTRLEN);
                printf("Client connected: socket=%d from %s:%d\n", 
                    new_socket, client_ip, ntohs(address.sin_port));

                for (int i = 0; i < 30; i++) {
                    if (clients[i].sd == 0) {
                        clients[i].sd = new_socket;
                        clients[i].buf = NULL;
                        clients[i].buf_len = 0;
                        clients[i].buf_cap = 0;
                        clients[i].last_active = time(NULL);
                        break;
                    }
                }
            }
        }

        // handle client
        for (int i = 0; i < 30; i++) {
            ClientState *cs = &clients[i];
            int sd = cs->sd;
            if (sd <= 0) continue;
            if (!FD_ISSET(sd, &readfds)) continue;

            unsigned char tmp[4096];
            int r = recv(sd, tmp, sizeof(tmp), 0);
            if (r == 0) {
                // Đóng kết nối 
                handle_disconnect(sd);
                client_reset(cs);
                continue;
            } else if (r < 0) {
                if (errno != EWOULDBLOCK && errno != EAGAIN) {
                    handle_disconnect(sd);
                    client_reset(cs);
                }
                continue;
            }
            // Thêm dữ liệu vào buffer
            if (!ensure_capacity(cs, cs->buf_len + r)) {
                fprintf(stderr, "Failed to expand buffer for client %d\n", sd);
                handle_disconnect(sd);
                client_reset(cs);
                continue;
            }
            memcpy(cs->buf + cs->buf_len, tmp, r);
            cs->buf_len += r;
            process_client_buffer(cs);
        }

        time_t now = time(NULL);
        if (now - last_check >= 1) {  // Check every second for phase timeouts
            send_ping_to_all_clients();
            check_timeouts();
            check_role_card_timeouts();
            check_seer_phase_timeout();  // Check seer deadline
            check_guard_phase_timeout(); // Check guard deadline
            check_wolf_phase_timeout();  // Check wolf deadline and process votes
            check_day_phase_timeout();   // Check day deadline and process votes
            check_disconnect_timeouts(); // Check disconnected players (2 min timeout)
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