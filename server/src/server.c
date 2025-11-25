#include <stdio.h>
#include <sys/socket.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <mysql/mysql.h>
#include "cJSON.h"

#ifdef _WIN32
    #include <winsock2.h>
    #include <windows.h>
    #include <wincrypt.h>
    #pragma comment(lib, "advapi32.lib")
#else
    #include <openssl/sha.h>
#endif

#define PORT 5000

enum PacketHeader {
    LOGIN_REQ = 101,
    LOGIN_RES = 102,
    REGISTER_REQ = 103,
    REGISTER_RES = 104,
    LOGOUT_REQ = 105,

    GET_ROOMS_REQ = 201,
    GET_ROOMS_RES = 202,
    CREATE_ROOM_REQ = 203,
    CREATE_ROOM_RES = 204,
    JOIN_ROOM_REQ = 205,
    JOIN_ROOM_RES = 206,    
    ROOM_STATUS_UPDATE = 207,
    LEAVE_ROOM_REQ = 208,

    START_GAME_REQ = 301,
    GAME_START_RES_AND_ROLE = 302,
    PHASE_NIGHT = 303,
    PHASE_DAY = 304,
    GAME_OVER = 305,

    CHAT_REQ = 401,
    CHAT_BROADCAST = 402,
    WOLF_KILL_REQ = 403,
    SEER_CHECK_REQ = 404,
    SEER_RESULT = 405,
    GUARD_PROTECT_REQ = 406,
    VOTE_REQ = 407,
    VOTE_STATUS_UPDATE = 408,
    VOTE_RESULT = 409,

    ERROR_MSG = 500,
    PING = 501,
};

char ENV_HOST[256] = "localhost";
char ENV_USER[128] = "root";
char ENV_PASS[128] = "";
char ENV_NAME[128] = "werewolf_game";
int  ENV_PORT = 3306;

MYSQL *conn;

void load_env(){
    FILE *file = fopen("../.env", "r");
    if(file == NULL) {
        printf("Could not open .env file");
        return;
    }

    char line[512];
    while(fgets(line, sizeof(line), file)) {
        line[strcspn(line, "\n")] = 0;
        line[strcspn(line, "\r")] = 0;

        if (strlen(line) == 0 || line[0] == '#') continue;

        char *delimiter = strchr(line, '=');
        if (delimiter) {
            *delimiter = 0;
            char *key = line;
            char *val = delimiter + 1;

            if (strcmp(key, "DB_HOST") == 0) strcpy(ENV_HOST, val);
            else if (strcmp(key, "DB_USER") == 0) strcpy(ENV_USER, val);
            else if (strcmp(key, "DB_PASS") == 0) strcpy(ENV_PASS, val);
            else if (strcmp(key, "DB_NAME") == 0) strcpy(ENV_NAME, val);
            else if (strcmp(key, "DB_PORT") == 0) ENV_PORT = atoi(val);
        }
    }
    fclose(file);   
    printf("Environment variables loaded from .env file.\n");
}       

void connect_db(){
    conn = mysql_init(NULL);
    if (conn == NULL){
        fprintf(stderr, "mysql_init() failed\n");
        exit(1);
    }

    if (mysql_real_connect(conn, ENV_HOST, ENV_USER, ENV_PASS,
          ENV_NAME, ENV_PORT, NULL, 0) == NULL) {
        fprintf(stderr, "mysql_real_connect() failed\n");
        mysql_close(conn);
        exit(1);
    }
    printf("Connected to database successfully.\n");
}

char* escape_string(const char *str) {
    if (!str) return NULL;

    size_t len = strlen(str);
    char *escaped = malloc(len * 2 + 1);
    if (!escaped) return NULL;

    mysql_real_escape_string(conn, escaped, str, len);
    return escaped;
}

char* sha256_hash(const char *password) {
    if (!password) return NULL;

    unsigned char hash[32];
    char *hex_hash = malloc(65);
    if (!hex_hash) return NULL;

#ifdef _WIN32
    HCRYPTPROV hProv = 0;
    HCRYPTHASH hHash = 0;
    DWORD hash_len = 32;

    if (!CryptAcquireContext(&hProv, NULL, NULL, PROV_RSA_AES, CRYPT_VERIFYCONTEXT)) {
        free(hex_hash);
        return NULL;
    }

    if (!CryptCreateHash(hProv, CALG_SHA_256, 0, 0, &hHash)) {
        CryptReleaseContext(hProv, 0);
        free(hex_hash);
        return NULL;
    }

    if (!CryptHashData(hHash, (BYTE*)password, strlen(password), 0)) {
        CryptDestroyHash(hHash);
        CryptReleaseContext(hProv, 0);
        free(hex_hash);
        return NULL;
    }

    if (!CryptGetHashParam(hHash, HP_HASHVAL, hash, &hash_len, 0)) {
        CryptDestroyHash(hHash);
        CryptReleaseContext(hProv, 0);
        free(hex_hash);
        return NULL;
    }

    CryptDestroyHash(hHash);
    CryptReleaseContext(hProv, 0);
#else
    SHA256((unsigned char*)password, strlen(password), hash);
#endif

    for (int i = 0; i < 32; i++) {
        sprintf(hex_hash + (i * 2), "%02x", hash[i]);
    }
    hex_hash[64] = '\0';

    return hex_hash;
}

void send_packet(int client_fd, uint16_t header, const char *payload) {
    uint32_t len = strlen(payload);

    uint16_t h = htons(header);
    uint32_t l = htonl(len);

    char *buffer = malloc(6 + len);
    if (!buffer) {
        fprintf(stderr, "Failed to allocate memory for packet\n");
        return;
    }

    memcpy(buffer,     &h, 2);
    memcpy(buffer + 2, &l, 4);
    memcpy(buffer + 6, payload, len);

    send(client_fd, buffer, 6 + len, 0);

    free(buffer);
}

void handle_register(int client_fd, cJSON *json){
    cJSON *user = cJSON_GetObjectItemCaseSensitive(json, "username");
    cJSON *pass = cJSON_GetObjectItemCaseSensitive(json, "password");

    cJSON *response = cJSON_CreateObject();

    if (!user || !pass || !cJSON_IsString(user) || !cJSON_IsString(pass)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Missing username or password");
    } else {
        char *hashed_pass = sha256_hash(pass->valuestring);

        if (!hashed_pass) {
            cJSON_AddStringToObject(response, "status", "error");
            cJSON_AddStringToObject(response, "message", "Server error");
        } else {
            char *escaped_user = escape_string(user->valuestring);
            char *escaped_hash = escape_string(hashed_pass);

            if (!escaped_user || !escaped_hash) {
                cJSON_AddStringToObject(response, "status", "error");
                cJSON_AddStringToObject(response, "message", "Server error");
                free(escaped_user);
                free(escaped_hash);
                free(hashed_pass);
            } else {
                char query[2048];
                snprintf(query, sizeof(query),
                         "INSERT INTO user (username, password_hash) VALUES ('%s', '%s')",
                         escaped_user, escaped_hash);

                if (mysql_query(conn, query)) {
                    cJSON_AddStringToObject(response, "status", "fail");
                    cJSON_AddStringToObject(response, "message", "Username already exists");
                } else {
                    cJSON_AddStringToObject(response, "status", "success");
                    printf("New user registered: %s\n", user->valuestring);
                }

                free(escaped_user);
                free(escaped_hash);
                free(hashed_pass);
            }
        }
    }

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, REGISTER_RES, res_str);

    free(res_str);
    cJSON_Delete(response);
}

void handle_login(int client_fd, cJSON *json){
    cJSON *user = cJSON_GetObjectItemCaseSensitive(json, "username");
    cJSON *pass = cJSON_GetObjectItemCaseSensitive(json, "password");

    cJSON *response = cJSON_CreateObject();

    if (!user || !pass || !cJSON_IsString(user) || !cJSON_IsString(pass)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Missing username or password");
    } else {
        char *hashed_pass = sha256_hash(pass->valuestring);

        if (!hashed_pass) {
            cJSON_AddStringToObject(response, "status", "error");
            cJSON_AddStringToObject(response, "message", "Server error");
        } else {
            char *escaped_user = escape_string(user->valuestring);
            char *escaped_hash = escape_string(hashed_pass);

            if (!escaped_user || !escaped_hash) {
                cJSON_AddStringToObject(response, "status", "error");
                cJSON_AddStringToObject(response, "message", "Server error");
                free(escaped_user);
                free(escaped_hash);
                free(hashed_pass);
            } else {
                char query[2048];
                snprintf(query, sizeof(query),
                         "SELECT user_id FROM user WHERE username='%s' AND password_hash='%s'",
                         escaped_user, escaped_hash);

                if (mysql_query(conn, query) == 0) {
                    MYSQL_RES *result = mysql_store_result(conn);
                    if (result && mysql_num_rows(result) > 0) {
                        MYSQL_ROW row = mysql_fetch_row(result);
                        int user_id = atoi(row[0]);

                        cJSON_AddStringToObject(response, "status", "success");
                        cJSON_AddNumberToObject(response, "user_id", user_id);
                        printf("User login: %s (ID: %d)\n", user->valuestring, user_id);
                    } else {
                        cJSON_AddStringToObject(response, "status", "fail");
                        cJSON_AddStringToObject(response, "message", "Wrong username or password");
                    }
                    mysql_free_result(result);
                } else {
                    cJSON_AddStringToObject(response, "status", "error");
                    cJSON_AddStringToObject(response, "message", "Database error");
                }

                free(escaped_user);
                free(escaped_hash);
                free(hashed_pass);
            }
        }
    }

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, LOGIN_RES, res_str);

    free(res_str);
    cJSON_Delete(response);
}

void process_packet(int client_fd, uint16_t header, const char *payload) {
    cJSON *json = cJSON_Parse(payload);
    if (!json) {
        printf("Invalid JSON payload from client %d\n", client_fd);
        return;
    }

    switch (header) {
        case REGISTER_REQ:
            handle_register(client_fd, json);
            break;
        case LOGIN_REQ:
            handle_login(client_fd, json);
            break;
        default:
            printf("Unknown packet header: %d\n", header);
            break;
    }

    cJSON_Delete(json);
}

int main() {
    load_env();
    connect_db();

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

                if (length > 65536) {
                    printf("Payload too large from client %d, disconnecting\n", sd);
                    close(sd);
                    clients[i] = 0;
                    continue;
                }

                char *payload = malloc(length + 1);
                if (!payload) {
                    fprintf(stderr, "Failed to allocate memory for payload\n");
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
    }

    mysql_close(conn);
    return 0;
}
