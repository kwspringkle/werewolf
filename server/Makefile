# Makefile for Werewolf Game Server

CC = gcc
CFLAGS = -Wall -Wextra -g -I/usr/include/mysql
LDFLAGS = -lmysqlclient -lssl -lcrypto
TARGET = server
SRC_DIR = src
BUILD_DIR = build

SOURCES = $(SRC_DIR)/server.c $(SRC_DIR)/cJSON.c
OBJECTS = $(BUILD_DIR)/server.o $(BUILD_DIR)/cJSON.o

# Default target
all: $(BUILD_DIR) $(TARGET)

# Create build directory
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# Link object files to create executable
$(TARGET): $(OBJECTS)
	$(CC) $(OBJECTS) -o $(TARGET) $(LDFLAGS)
	@echo "Build complete! Run with: ./$(TARGET)"

# Compile server.c
$(BUILD_DIR)/server.o: $(SRC_DIR)/server.c
	$(CC) $(CFLAGS) -c $< -o $@

# Compile cJSON.c
$(BUILD_DIR)/cJSON.o: $(SRC_DIR)/cJSON.c
	$(CC) $(CFLAGS) -c $< -o $@

# Clean build artifacts
clean:
	rm -rf $(BUILD_DIR) $(TARGET)
	@echo "Clean complete!"

# Run the server
run: $(TARGET)
	./$(TARGET)

# Rebuild everything
rebuild: clean all

.PHONY: all clean run rebuild
