#ifndef ROLE_MANAGER_H
#define ROLE_MANAGER_H

#include "types.h"
#include "cJSON.h"
#include "protocol.h"

// Get role info as JSON (name, description, icon)
cJSON* get_role_info_json(int room_index, int player_index);

// Get werewolf team members (returns array of usernames)
cJSON* get_werewolf_team(int room_index, int player_index);

// Send role info to a player
void send_role_info_to_player(int room_index, int player_index);

// Validate role distribution for player count
int validate_role_distribution(int num_players, int *num_werewolves, int *num_seer, 
                               int *num_guard, int *num_villagers);

#endif // ROLE_MANAGER_H
