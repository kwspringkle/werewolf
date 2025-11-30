# ===============================
#  Werewolf Client Makefile
# ===============================

CC = gcc
CFLAGS = -Wall -O2 -fPIC
TARGET = libwerewolf_client.so
OBJ = werewolf_client.o

# ===============================
#  Build shared library (.so)
# ===============================
all: $(TARGET)

$(OBJ): werewolf_client.c werewolf_client.h
	$(CC) $(CFLAGS) -c werewolf_client.c -o $(OBJ)

$(TARGET): $(OBJ)
	$(CC) -shared -o $(TARGET) $(OBJ)

# ===============================
#  Clean
# ===============================
clean:
	rm -f *.o *.so example *.dll *.a

.PHONY: all clean example
