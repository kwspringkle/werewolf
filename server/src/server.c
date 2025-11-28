#include <stdio.h>
#include <sys/socket.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <mysql/mysql.h>
#include <time.h>
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

#define MAX_ROOMS 10
#define MAX_PLAYERS_PER_ROOM 12
#define MIN_PLAYERS_TO_START 6
#define MAX_SESSIONS 30

enum RoomStatus {
    ROOM_WAITING = 0,
    ROOM_PLAYING = 1
};

typedef struct {
    int socket;
    int user_id;
    char username[50];
    int is_logged_in;
    time_t last_ping;
} Session;

typedef struct {
    int socket;
    int user_id;
    char username[50];
    int role;
} Player;


typedef struct {
    int id;
    char name[50];
    Player players[MAX_PLAYERS_PER_ROOM];
    int current_players;
    int status;
    int host_socket;
} Room;

Room rooms[MAX_ROOMS];
Session sessions[MAX_SESSIONS];

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
    LEAVE_ROOM_RES = 209,
    GET_ROOM_INFO_REQ = 210,
    GET_ROOM_INFO_RES = 211,

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

// Function declarations
void send_packet(int client_fd, uint16_t header, const char *payload);
void handle_disconnect(int client_fd);
void add_session(int socket, int user_id, const char *username);
Session* find_session(int socket);
int get_user_room(int socket);

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

void handle_ping(int client_fd, cJSON *json) {
    (void)json;
    cJSON *pong = cJSON_CreateObject();
    cJSON_AddStringToObject(pong, "type", "pong");
    char *pong_str = cJSON_PrintUnformatted(pong);

    send_packet(client_fd, PING, pong_str);

    free(pong_str);
    cJSON_Delete(pong);
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

                        add_session(client_fd, user_id, user->valuestring);

                        cJSON_AddStringToObject(response, "status", "success");
                        cJSON_AddNumberToObject(response, "user_id", user_id);
                        cJSON_AddStringToObject(response, "username", user->valuestring);
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

void init_room() {
    for (int i = 0; i < MAX_ROOMS; i++) {
        rooms[i].id = 0;
        rooms[i].name[0] = '\0';
        rooms[i].current_players = 0;
        rooms[i].status = ROOM_WAITING;
        rooms[i].host_socket = 0;
    }
}

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

void handle_create_room(int client_fd, cJSON *json) {
    Session *session = find_session(client_fd);
    cJSON *response = cJSON_CreateObject();

    if (!session) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Please login first");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, CREATE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int current_room = get_user_room(client_fd);
    if (current_room != -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "You are already in a room");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, CREATE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    cJSON *room_name = cJSON_GetObjectItem(json, "room_name");
    if (!room_name || !cJSON_IsString(room_name)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid room name");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, CREATE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    size_t name_len = strlen(room_name->valuestring);
    if (name_len == 0 || name_len >= 50) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Room name must be 1-49 characters");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, CREATE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_index = -1;
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == 0) {
            room_index = i;
            break;
        }
    }

    if (room_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "No available rooms");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, CREATE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    rooms[room_index].id = room_index + 1;
    strncpy(rooms[room_index].name, room_name->valuestring, sizeof(rooms[room_index].name) - 1);
    rooms[room_index].name[49] = '\0'; 
    rooms[room_index].current_players = 1;
    rooms[room_index].status = ROOM_WAITING;
    rooms[room_index].host_socket = client_fd;

    rooms[room_index].players[0].socket = client_fd;
    rooms[room_index].players[0].user_id = session->user_id;
    strncpy(rooms[room_index].players[0].username, session->username, sizeof(rooms[room_index].players[0].username) - 1);

    cJSON_AddStringToObject(response, "status", "success");
    cJSON_AddNumberToObject(response, "room_id", rooms[room_index].id);
    cJSON_AddStringToObject(response, "room_name", rooms[room_index].name);

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, CREATE_ROOM_RES, res_str);
    free(res_str);
    cJSON_Delete(response);
    printf("Room created: %s by %s (user_id: %d)\n", room_name->valuestring, session->username, session->user_id);
}

void handle_get_rooms(int client_fd) {
    cJSON *response = cJSON_CreateArray();

    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id != 0) {
            cJSON *room_item = cJSON_CreateObject();
            cJSON_AddNumberToObject(room_item, "id", rooms[i].id);
            cJSON_AddStringToObject(room_item, "name", rooms[i].name);
            cJSON_AddNumberToObject(room_item, "current", rooms[i].current_players);
            cJSON_AddNumberToObject(room_item, "max", MAX_PLAYERS_PER_ROOM);
            cJSON_AddNumberToObject(room_item, "status", rooms[i].status);
            cJSON_AddItemToArray(response, room_item);
        }
    }

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, GET_ROOMS_RES, res_str);

    free(res_str);
    cJSON_Delete(response);
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

void handle_join_room(int client_fd, cJSON *json) {
    Session *session = find_session(client_fd);

    cJSON *response = cJSON_CreateObject();

    if (!session) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Please login first");
        send_packet(client_fd, JOIN_ROOM_RES, cJSON_PrintUnformatted(response));
        cJSON_Delete(response);
        return;
    }

    int current_room = get_user_room(client_fd);
    if (current_room != -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "You are already in a room");
        send_packet(client_fd, JOIN_ROOM_RES, cJSON_PrintUnformatted(response));
        cJSON_Delete(response);
        return;
    }

    cJSON *room_id_obj = cJSON_GetObjectItemCaseSensitive(json, "room_id");
    if (!room_id_obj || !cJSON_IsNumber(room_id_obj)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid or missing room_id");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, JOIN_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_id = room_id_obj->valueint;

    if (room_id < 1 || room_id > MAX_ROOMS) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid room_id");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, JOIN_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_index = -1;
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == room_id) {
            room_index = i;
            break;
        }
    }

    if (room_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Room not found");
        send_packet(client_fd, JOIN_ROOM_RES, cJSON_PrintUnformatted(response));
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].status == ROOM_PLAYING) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Game already started");
        send_packet(client_fd, JOIN_ROOM_RES, cJSON_PrintUnformatted(response));
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].current_players >= MAX_PLAYERS_PER_ROOM) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Room is full");
        send_packet(client_fd, JOIN_ROOM_RES, cJSON_PrintUnformatted(response));
        cJSON_Delete(response);
        return;
    }

    int idx = rooms[room_index].current_players;
    rooms[room_index].players[idx].socket = client_fd;
    rooms[room_index].players[idx].user_id = session->user_id;
    strncpy(rooms[room_index].players[idx].username, session->username, sizeof(rooms[room_index].players[idx].username) - 1);
    rooms[room_index].players[idx].username[49] = '\0';
    rooms[room_index].current_players++;

    cJSON_AddStringToObject(response, "status", "success");
    cJSON_AddNumberToObject(response, "is_host", 0);
    cJSON_AddNumberToObject(response, "room_id", rooms[room_index].id);
    cJSON_AddStringToObject(response, "room_name", rooms[room_index].name);

    cJSON *player_list = cJSON_CreateArray();
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        cJSON *p = cJSON_CreateObject();
        cJSON_AddStringToObject(p, "username", rooms[room_index].players[i].username);
        cJSON_AddItemToArray(player_list, p);
    }
    cJSON_AddItemToObject(response, "players", player_list);

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, JOIN_ROOM_RES, res_str);
    free(res_str);
    cJSON_Delete(response);

    cJSON *update = cJSON_CreateObject();
    cJSON_AddStringToObject(update, "type", "player_joined");
    cJSON_AddStringToObject(update, "username", session->username);
    cJSON_AddNumberToObject(update, "current_players", rooms[room_index].current_players);

    char *update_str = cJSON_PrintUnformatted(update);
    broadcast_room(room_index, ROOM_STATUS_UPDATE, update_str);
    free(update_str);
    cJSON_Delete(update);

    printf("Player %s joined room %d\n", session->username, room_id);
}

void handle_disconnect(int client_fd) {
    Session *session = find_session(client_fd);

    if (session) {
        printf("User %s disconnected (socket: %d)\n", session->username, client_fd);

        int room_index = get_user_room(client_fd);
        if (room_index != -1) {
            int player_index = -1;
            for (int i = 0; i < rooms[room_index].current_players; i++) {
                if (rooms[room_index].players[i].socket == client_fd) {
                    player_index = i;
                    break;
                }
            }

            if (player_index != -1) {
                char username[50];
                strncpy(username, rooms[room_index].players[player_index].username, sizeof(username) - 1);

                for (int i = player_index; i < rooms[room_index].current_players - 1; i++) {
                    rooms[room_index].players[i] = rooms[room_index].players[i + 1];
                }
                rooms[room_index].current_players--;

                if (rooms[room_index].current_players == 0) {
                    printf("Room %d is now empty and will be deleted\n", rooms[room_index].id);
                    rooms[room_index].id = 0;
                    rooms[room_index].name[0] = '\0';
                    rooms[room_index].status = ROOM_WAITING;
                    rooms[room_index].host_socket = 0;
                } else {
                    if (rooms[room_index].host_socket == client_fd) {
                        rooms[room_index].host_socket = rooms[room_index].players[0].socket;
                        printf("Host changed to %s in room %d\n",
                               rooms[room_index].players[0].username, rooms[room_index].id);
                    }

                    cJSON *update = cJSON_CreateObject();
                    cJSON_AddStringToObject(update, "type", "player_left");
                    cJSON_AddStringToObject(update, "username", username);
                    cJSON_AddNumberToObject(update, "current_players", rooms[room_index].current_players);

                    char *update_str = cJSON_PrintUnformatted(update);
                    broadcast_room(room_index, ROOM_STATUS_UPDATE, update_str);
                    free(update_str);
                    cJSON_Delete(update);
                }
            }
        }

        remove_session(client_fd);
    } else {
        printf("Client %d disconnected (not logged in)\n", client_fd);
    }
}

void handle_leave_room(int client_fd, cJSON *json) {
    (void)json;
    Session *session = find_session(client_fd);
    cJSON *response = cJSON_CreateObject();

    if (!session) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Please login first");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, LEAVE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_index = get_user_room(client_fd);
    if (room_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "You are not in any room");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, LEAVE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].status == ROOM_PLAYING) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Cannot leave room while game is in progress");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, LEAVE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int player_index = -1;
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (rooms[room_index].players[i].socket == client_fd) {
            player_index = i;
            break;
        }
    }

    if (player_index == -1){
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "You are not in this room");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, LEAVE_ROOM_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    char username [50];
    strncpy(username, rooms[room_index].players[player_index].username, sizeof(username) - 1);
    username[49] = '\0';

    for (int i = player_index; i < rooms[room_index].current_players - 1; i++) {
        rooms[room_index].players[i] = rooms[room_index].players[i + 1];
    }
    rooms[room_index].current_players--;

    cJSON_AddStringToObject(response, "status", "success");
    cJSON_AddStringToObject(response, "message", "Left room successfully");
    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, LEAVE_ROOM_RES, res_str);
    free(res_str);
    cJSON_Delete(response);

    printf("Player %s left room %d\n", username, rooms[room_index].id);

    if (rooms[room_index].current_players == 0) {
        printf("Room %d is now empty and will be deleted\n", rooms[room_index].id);
        rooms[room_index].id = 0;
        rooms[room_index].name[0] = '\0';
        rooms[room_index].status = ROOM_WAITING;
        rooms[room_index].host_socket = 0;
    } 

    if (rooms[room_index].host_socket == client_fd) {
        rooms[room_index].host_socket = rooms[room_index].players[0].socket;
        printf("Host changed to %s in room %d\n",
               rooms[room_index].players[0].username, rooms[room_index].id);
    }

    cJSON *update = cJSON_CreateObject();
    cJSON_AddStringToObject(update, "type", "player_left");
    cJSON_AddStringToObject(update, "username", username);
    cJSON_AddNumberToObject(update, "current_players", rooms[room_index].current_players);

    char *update_str = cJSON_PrintUnformatted(update);
    broadcast_room(room_index, ROOM_STATUS_UPDATE, update_str);
    free(update_str);
    cJSON_Delete(update);
}

void handle_get_room_info(int client_fd, cJSON *json) {
    cJSON *response = cJSON_CreateObject();

    cJSON *room_id_obj = cJSON_GetObjectItemCaseSensitive(json, "room_id");
    if (!room_id_obj || !cJSON_IsNumber(room_id_obj)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid room ID");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, GET_ROOM_INFO_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_id = room_id_obj->valueint;

    int room_index = -1;
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == room_id) {
            room_index = i;
            break;
        }
    }

    if (room_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Room not found");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, GET_ROOM_INFO_RES, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    cJSON_AddStringToObject(response, "status", "success");
    cJSON_AddNumberToObject(response, "room_id", rooms[room_index].id);
    cJSON_AddStringToObject(response, "room_name", rooms[room_index].name);
    cJSON_AddNumberToObject(response, "current_players", rooms[room_index].current_players);
    cJSON_AddNumberToObject(response, "max_players", MAX_PLAYERS_PER_ROOM);
    cJSON_AddNumberToObject(response, "status", rooms[room_index].status);

    cJSON *players = cJSON_CreateArray();
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        cJSON *player = cJSON_CreateObject();
        cJSON_AddStringToObject(player, "username", rooms[room_index].players[i].username);
        cJSON_AddNumberToObject(player, "user_id", rooms[room_index].players[i].user_id);

        int is_host = (rooms[room_index].players[i].socket == rooms[room_index].host_socket) ? 1 : 0;
        cJSON_AddNumberToObject(player, "is_host", is_host);

        cJSON_AddItemToArray(players, player);
    }

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, GET_ROOM_INFO_RES, res_str);
    free(res_str);
    cJSON_Delete(response);
}

void handle_start_game(int client_fd, cJSON *json) {
    cJSON *response = cJSON_CreateObject();

    cJSON *room_id_obj = cJSON_GetObjectItemCaseSensitive(json, "room_id");
    if (!room_id_obj || !cJSON_IsNumber(room_id_obj)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid or missing room_id");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }
    int room_id = room_id_obj->valueint;

    if (room_id < 1 || room_id > MAX_ROOMS) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid room_id");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    int room_index = -1;
    for (int i = 0; i < MAX_ROOMS; i++) {
        if (rooms[i].id == room_id) {
            room_index = i;
            break;
        }
    }

    if (room_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Room not found");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].host_socket != client_fd) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Only host can start the game");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].current_players < MIN_PLAYERS_TO_START) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Need at least 6 players to start");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    if (rooms[room_index].status == ROOM_PLAYING) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Game already started");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, START_GAME_REQ, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    rooms[room_index].status = ROOM_PLAYING;

    cJSON_AddStringToObject(response, "status", "success");
    cJSON_AddStringToObject(response, "message", "Game started");

    char *res_str = cJSON_PrintUnformatted(response);
    broadcast_room(room_index, GAME_START_RES_AND_ROLE, res_str);

    free(res_str);
    cJSON_Delete(response);

    printf("Game started in room %d with %d players\n", room_id, rooms[room_index].current_players);
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
        case GET_ROOMS_REQ:
            handle_get_rooms(client_fd);
            break;
        case CREATE_ROOM_REQ:
            handle_create_room(client_fd, json);
            break;
        case JOIN_ROOM_REQ:
            handle_join_room(client_fd, json);
            break;
        case START_GAME_REQ:
            handle_start_game(client_fd, json);
            break;
        case LEAVE_ROOM_REQ:
            handle_leave_room(client_fd, json);
            break;
        case GET_ROOM_INFO_REQ:
            handle_get_room_info(client_fd, json);
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
    init_room();
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
