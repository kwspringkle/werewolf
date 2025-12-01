#ifndef DATABASE_H
#define DATABASE_H

#include <mysql/mysql.h>
#include "cJSON.h" 
extern MYSQL *conn;
extern char ENV_HOST[256];
extern char ENV_USER[128];
extern char ENV_PASS[128];
extern char ENV_NAME[128];
extern int ENV_PORT;

void load_env();
void connect_db();
char* escape_string(const char *str);
char* sha256_hash(const char *password);

#endif