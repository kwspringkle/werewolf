#include <stdio.h>
#include "role_handlers/seer_handler.h"
#include "cJSON.h"
#include "types.h"
#include <string.h>
#include "packet_handler.h"
#include "protocol.h"
#include "room_manager.h"

void seer_get_info(int room_index, int player_index, cJSON *info_obj) {
    cJSON_AddStringToObject(info_obj, "role_name", "Seer");
    cJSON_AddStringToObject(info_obj, "role_icon", "🔮");
    cJSON_AddStringToObject(info_obj, "role_description",
        "You are the SEER! Each night, you can check one player to know if they are a werewolf or not. Use your knowledge wisely to guide the village.");
}

// Xử lý phần gửi tin của role tiên tri
void seer_handle_packet(int client_fd, cJSON *json) {
    cJSON *response = cJSON_CreateObject();

    cJSON *room_id_obj = cJSON_GetObjectItemCaseSensitive(json, "room_id");
    cJSON *target_obj = cJSON_GetObjectItemCaseSensitive(json, "target_username");

    if (!room_id_obj || !cJSON_IsNumber(room_id_obj) || !target_obj || !cJSON_IsString(target_obj)) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid or missing room_id/target_username");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, SEER_RESULT, res_str);
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
        send_packet(client_fd, SEER_RESULT, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    // Tìm người đang gửi request
    int requester_index = -1;
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (rooms[room_index].players[i].socket == client_fd) {
            requester_index = i;
            break;
        }
    }

    if (requester_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "You are not in this room");
        char *res_str = cJSON_PrintUnformatted(response);
        send_packet(client_fd, SEER_RESULT, res_str);
        free(res_str);
        cJSON_Delete(response);
        return;
    }

    // Gửi danh sách người chơi và trạng thái alive
    cJSON *players_array = cJSON_AddArrayToObject(response, "players");
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        cJSON *player_obj = cJSON_CreateObject();
        cJSON_AddStringToObject(player_obj, "username", rooms[room_index].players[i].username);
        cJSON_AddBoolToObject(player_obj, "is_alive", rooms[room_index].players[i].is_alive);
        cJSON_AddItemToArray(players_array, player_obj);
    }

    // Gọi hàm xử lý chính
    seer_handle_check(room_index, requester_index, target_obj->valuestring, response);

    char *res_str = cJSON_PrintUnformatted(response);
    send_packet(client_fd, SEER_RESULT, res_str);
    free(res_str);
    cJSON_Delete(response);
}

void seer_handle_check(int room_index, int requester_index, const char *target_username, cJSON *response) {
    if (room_index < 0 || room_index >= MAX_ROOMS) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Invalid room index");
        return;
    }

    if (requester_index < 0 || requester_index >= rooms[room_index].current_players) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Requester not in room");
        return;
    }

    Player *requester = &rooms[room_index].players[requester_index];
    // Kiểm tra có còn sống không
    if (!requester->is_alive || requester->role != ROLE_SEER) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "You are not an alive Seer");
        return;
    }

    // Chỉ khi đang ở trong ban đêm 
    if (!rooms[room_index].night_phase_active) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Night phase is not active");
        return;
    }

    // Đảm bảo tiên tri chưa chọn trong đêm nay
    if (rooms[room_index].seer_choice_made) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Seer has already made a choice this night");
        return;
    }

    // Đảm bảo chưa quá deadline để chọn
    time_t now = time(NULL);
    if (rooms[room_index].seer_deadline != 0 && now > rooms[room_index].seer_deadline) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Seer selection window has expired");
        return;
    }

    int target_index = -1;
    for (int i = 0; i < rooms[room_index].current_players; i++) {
        if (strcmp(rooms[room_index].players[i].username, target_username) == 0) {
            target_index = i;
            break;
        }
    }

    if (target_index == -1) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Target player not found");
        return;
    }

    // Kiểm tra target còn sống không
    if (!rooms[room_index].players[target_index].is_alive) {
        cJSON_AddStringToObject(response, "status", "fail");
        cJSON_AddStringToObject(response, "message", "Target is already dead");
        return;
    }

    int is_werewolf = (rooms[room_index].players[target_index].role == ROLE_WEREWOLF) ? 1 : 0;

    // Lưu lại lựa chọn của tiên tri
    rooms[room_index].seer_choice_made = 1;
    strncpy(rooms[room_index].seer_chosen_target, target_username, sizeof(rooms[room_index].seer_chosen_target) - 1);
    rooms[room_index].seer_chosen_target[sizeof(rooms[room_index].seer_chosen_target) - 1] = '\0';

    cJSON_AddStringToObject(response, "status", "success");
    cJSON_AddStringToObject(response, "target_username", target_username);
    cJSON_AddBoolToObject(response, "is_werewolf", is_werewolf);
    
    // Báo tất cả client chuyển sang guard phase
    printf("[SERVER] Seer has made choice, broadcasting PHASE_GUARD_START to all players in room %d\n", rooms[room_index].id);
    cJSON *guard_notif = cJSON_CreateObject();
    cJSON_AddStringToObject(guard_notif, "type", "phase_guard_start");
    cJSON_AddNumberToObject(guard_notif, "guard_duration", GUARD_PHASE_DURATION);
    char *guard_notif_str = cJSON_PrintUnformatted(guard_notif);
    broadcast_room(room_index, PHASE_GUARD_START, guard_notif_str);
    free(guard_notif_str);
    cJSON_Delete(guard_notif);
}
