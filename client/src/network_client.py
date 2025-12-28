"""
Network Client - Python wrapper for C library
Uses ctypes to call C socket functions
"""

import ctypes
import json
import os
import platform
from pathlib import Path


class WerewolfNetworkClient:
    def send_wolf_kill(self, room_id, target_username):
        """Gửi yêu cầu sói cắn (wolf kill)"""
        if not self.client:
            raise RuntimeError("Client not created")
        if not hasattr(self.lib, 'ww_client_wolf_kill_send'):
            raise RuntimeError("C library missing wolf kill send")
        if not isinstance(target_username, str):
            raise ValueError("target_username must be a string")
        result = self.lib.ww_client_wolf_kill_send(self.client, int(room_id), target_username.encode('utf-8'))
        if result < 0:
            error = self.get_error()
            raise RuntimeError(f"Send wolf kill failed: {error}")
        return result
    def send_seer_check(self, room_id, target_username):
        """Gửi yêu cầu tiên tri (seer check)"""
        if not self.client:
            raise RuntimeError("Client not created")
        if not hasattr(self.lib, 'ww_client_seer_check_send'):
            raise RuntimeError("C library missing seer check send")
        if not isinstance(target_username, str):
            raise ValueError("target_username must be a string")
        result = self.lib.ww_client_seer_check_send(self.client, int(room_id), target_username.encode('utf-8'))
        if result < 0:
            error = self.get_error()
            raise RuntimeError(f"Send seer check failed: {error}")
        return result
    def send_guard_protect(self, room_id, target_username):
        """Gửi yêu cầu bảo vệ (guard protect)"""
        if not self.client:
            raise RuntimeError("Client not created")
        if not hasattr(self.lib, 'ww_client_guard_protect_send'):
            raise RuntimeError("C library missing guard protect send")
        if not isinstance(target_username, str):
            raise ValueError("target_username must be a string")
        result = self.lib.ww_client_guard_protect_send(self.client, int(room_id), target_username.encode('utf-8'))
        if result < 0:
            error = self.get_error()
            raise RuntimeError(f"Send guard protect failed: {error}")
        return result

    """Python wrapper cho C Werewolf Network Client, sử dụng ctypes"""
    
    def __init__(self):
        self.client = None
        self.lib = None
        self._load_library()
        
    def _load_library(self):
        """Tìm file thư viện đã compile"""
        if platform.system() == "Windows":
            lib_names = ["werewolf_client.dll", "libwerewolf_client.dll"]
        else:
            lib_names = ["libwerewolf_client.so", "werewolf_client.so"]
            
        lib_path = None
        lib_dir = Path(__file__).parent.parent / "lib"
        
        for lib_name in lib_names:
            candidate = lib_dir / lib_name
            if candidate.exists():
                lib_path = candidate
                break
        
        if not lib_path:
            raise FileNotFoundError(
                f"Library not found in: {lib_dir}\n"
                f"Looking for: {', '.join(lib_names)}\n"
                f"Please compile the C library first:\n"
                f"  cd {lib_dir}\n"
                f"  make"
            )
            
        # Load thư viện
        self.lib = ctypes.CDLL(str(lib_path))
        
        # Định nghĩa chữ ký hàm
        self._define_functions()
        
    def _define_functions(self):
        # ww_client_wolf_kill_send(client, room_id, target_username) -> int
        if hasattr(self.lib, 'ww_client_wolf_kill_send'):
            self.lib.ww_client_wolf_kill_send.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
            self.lib.ww_client_wolf_kill_send.restype = ctypes.c_int
        
        """Định nghĩa chữ ký hàm C"""
        # ww_client_create() -> WerewolfClient*
        self.lib.ww_client_create.argtypes = []
        self.lib.ww_client_create.restype = ctypes.c_void_p
        
        # ww_client_connect(client, host, port) -> int
        self.lib.ww_client_connect.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int
        ]
        self.lib.ww_client_connect.restype = ctypes.c_int
        
        # ww_client_send(client, header, payload) -> int
        self.lib.ww_client_send.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ushort,
            ctypes.c_char_p
        ]
        self.lib.ww_client_send.restype = ctypes.c_int
        
        # ww_client_receive(client, out_header, out_payload, max_size) -> int
        self.lib.ww_client_receive.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ushort),
            ctypes.c_char_p,
            ctypes.c_int
        ]
        self.lib.ww_client_receive.restype = ctypes.c_int
        
        # ww_client_disconnect(client)
        self.lib.ww_client_disconnect.argtypes = [ctypes.c_void_p]
        self.lib.ww_client_disconnect.restype = None
        
        # ww_client_destroy(client)
        self.lib.ww_client_destroy.argtypes = [ctypes.c_void_p]
        self.lib.ww_client_destroy.restype = None
        
        # ww_client_get_error(client) -> const char*
        self.lib.ww_client_get_error.argtypes = [ctypes.c_void_p]
        self.lib.ww_client_get_error.restype = ctypes.c_char_p

        # ww_client_seer_check_send(client, room_id, target_username) -> int
        if hasattr(self.lib, 'ww_client_seer_check_send'):
            self.lib.ww_client_seer_check_send.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
            self.lib.ww_client_seer_check_send.restype = ctypes.c_int

        # ww_client_guard_protect_send(client, room_id, target_username) -> int
        if hasattr(self.lib, 'ww_client_guard_protect_send'):
            self.lib.ww_client_guard_protect_send.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
            self.lib.ww_client_guard_protect_send.restype = ctypes.c_int
        
    def create(self):
        """Tạo instance client"""
        self.client = self.lib.ww_client_create()
        if not self.client:
            raise RuntimeError("Failed to create client")
        return self
        
    def connect(self, host, port):
        """Kết nối đến server"""
        if not self.client:
            raise RuntimeError("Client not created")
            
        host_bytes = host.encode('utf-8')
        result = self.lib.ww_client_connect(self.client, host_bytes, port)
        
        if result != 0:
            error = self.get_error()
            raise ConnectionError(f"Connection failed: {error}")
            
        return True
        
    def send_packet(self, header, payload_dict):
        """Gửi gói tin đến server"""
        if not self.client:
            raise RuntimeError("Client not created")
            
        payload_json = json.dumps(payload_dict)
        payload_bytes = payload_json.encode('utf-8')
        
        result = self.lib.ww_client_send(self.client, header, payload_bytes)
        
        if result < 0:
            error = self.get_error()
            raise RuntimeError(f"Send failed: {error}")
            
        return result
        
    def receive_packet(self):
        """
        Nhận gói tin từ server (không chặn)
        Trả về: (header, payload_dict) hoặc (None, None) nếu không có dữ liệu
        """
        if not self.client:
            raise RuntimeError("Client not created")
            
        header = ctypes.c_ushort()
        payload_buffer = ctypes.create_string_buffer(8192)
        
        result = self.lib.ww_client_receive(
            self.client,
            ctypes.byref(header),
            payload_buffer,
            8192
        )
        
        if result < 0:
            error = self.get_error()
            raise RuntimeError(f"Receive failed: {error}")
        elif result == 0:
            return None, None  # No data available
        else:
            # Parse payload JSON
            payload_str = payload_buffer.value.decode('utf-8')
            try:
                payload_dict = json.loads(payload_str) if payload_str else {}
            except json.JSONDecodeError:
                payload_dict = {"raw": payload_str}
                
            return header.value, payload_dict
            
    def disconnect(self):
        """Ngắt kết nối từ server"""
        if self.client:
            self.lib.ww_client_disconnect(self.client)
            
    def destroy(self):
        """Hủy instance client"""
        if self.client:
            self.lib.ww_client_destroy(self.client)
            self.client = None
            
    def get_error(self):
        """Lấy thông báo lỗi cuối cùng"""
        if not self.client:
            return "Client not created"
        error_bytes = self.lib.ww_client_get_error(self.client)
        return error_bytes.decode('utf-8') if error_bytes else "Unknown error"
        
    def __del__(self):
        """Dọn dẹp khi đối tượng bị hủy"""
        self.destroy()
