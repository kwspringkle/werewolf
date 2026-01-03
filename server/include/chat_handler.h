#ifndef CHAT_HANDLER_H
#define CHAT_HANDLER_H

#include "cJSON.h"

// Handle chat message request from client
void handle_chat_message(int client_fd, cJSON *json);

#endif // CHAT_HANDLER_H
