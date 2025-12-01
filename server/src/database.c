#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mysql/mysql.h>
#include <time.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <windows.h>
    #include <wincrypt.h>
    #pragma comment(lib, "advapi32.lib")
#else
    #include <openssl/sha.h>
#endif

#include "database.h"
#include "cJSON.h"

MYSQL *conn;
char ENV_HOST[256] = "localhost";
char ENV_USER[128] = "root";
char ENV_PASS[128] = "";
char ENV_NAME[128] = "werewolf_game";
int  ENV_PORT = 3306;

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