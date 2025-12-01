CC = gcc
CFLAGS = -Wall -Wextra -g -Iinclude
LDFLAGS = -lmysqlclient -lssl -lcrypto
TARGET = werewolf_server
SRC_DIR = src
BUILD_DIR = build
INC_DIR = include

SOURCES = $(SRC_DIR)/main.c $(SRC_DIR)/cJSON.c $(SRC_DIR)/database.c \
          $(SRC_DIR)/room_manager.c $(SRC_DIR)/session_manager.c \
          $(SRC_DIR)/packet_handler.c $(SRC_DIR)/role_manager.c \
          $(SRC_DIR)/role_handlers/werewolf_handler.c \
          $(SRC_DIR)/role_handlers/seer_handler.c \
          $(SRC_DIR)/role_handlers/guard_handler.c \
          $(SRC_DIR)/role_handlers/villager_handler.c
OBJECTS = $(SOURCES:$(SRC_DIR)/%.c=$(BUILD_DIR)/%.o)

# Default target
all: $(BUILD_DIR) $(TARGET)

# Tạo folder build nếu chưa tồn tại
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)
	mkdir -p $(BUILD_DIR)/role_handlers

# Liên kết các đối tượng để tạo tệp thực thi
$(TARGET): $(OBJECTS)
	$(CC) $(OBJECTS) -o $(TARGET) $(LDFLAGS)
	@echo "Build complete! Run with: ./$(TARGET)"

# Biên dịch các tệp .c thành .o
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c
	$(CC) $(CFLAGS) -c $< -o $@

# Dọn dẹp các tệp đã biên dịch
clean:
	rm -rf $(BUILD_DIR) $(TARGET)
	@echo "Clean complete!"

# Chạy server
run: $(TARGET)
	./$(TARGET)

# Rebuild
rebuild: clean all

.PHONY: all clean run rebuild