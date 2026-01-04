from PyQt5 import QtWidgets, QtCore, QtGui
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.user_header import UserHeader

class RoleCardWindow(QtWidgets.QWidget):
    """Window hiển thị role card với timer 30s"""
    
    def __init__(self, toast_manager=None, window_manager=None):
        super().__init__()
        self.toast_manager = toast_manager
        self.window_manager = window_manager
        self.role_data = {}
        self.total_time = 30
        self.remaining_time = 30
        self.start_time = None
        self.network_client = None
        self.room_id = None
        self.setObjectName("role_card_window")
        self.setWindowTitle("Your Role")
        self.setup_ui()
        
    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)
        # Lấy network client từ shared data
        self.network_client = self.window_manager.get_shared_data("network_client")
        self.room_id = self.window_manager.get_shared_data("current_room_id")
        
        # Set username cho user_header
        username = self.window_manager.get_shared_data("username", "Player")
        self.user_header.set_username(username)
        
        # Lấy role_data từ shared data nếu có
        role_info = self.window_manager.get_shared_data("role_info", {})
        if role_info:
            self.set_role_data(role_info)
        
        # Bắt đầu timer nếu chưa bắt đầu
        if self.start_time is None and self.role_data:
            self.start_time = time.time()
            self.remaining_time = self.total_time
            self.start_timer()
        elif self.start_time is not None:
            # Nếu timer đã bắt đầu, tính lại remaining_time dựa trên elapsed time
            elapsed = time.time() - self.start_time
            self.remaining_time = max(0, int(self.total_time - elapsed))
            # Restart timer nếu chưa hết thời gian
            if self.remaining_time > 0 and (not hasattr(self, 'countdown_timer') or not self.countdown_timer.isActive()):
                self.start_timer()
            
    def set_role_data(self, role_data):
        """Set role data và update UI"""
        self.role_data = role_data
        if self.start_time is None:
            self.start_time = time.time()
            self.remaining_time = self.total_time
        
        # Update UI với role data mới
        self.update_ui()
        
    def update_ui(self):
        """Update UI với role data hiện tại"""
        if not self.role_data:
            return
            
        # Update icon
        if hasattr(self, 'icon_label'):
            self.icon_label.setText(self.role_data.get("role_icon", "❓"))
        
        # Update role name
        if hasattr(self, 'role_label'):
            role_name = self.role_data.get("role_name", "Unknown")
            self.role_label.setText(role_name.upper())
        
        # Update description
        if hasattr(self, 'description_text'):
            self.description_text.setText(self.role_data.get("role_description", ""))
        
        # Update werewolf team
        if hasattr(self, 'team_container'):
            # Remove old team widgets
            while self.team_layout.count():
                item = self.team_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Add new team if exists
            if "werewolf_team" in self.role_data and self.role_data["werewolf_team"]:
                self.team_label.setVisible(True)
                for teammate in self.role_data["werewolf_team"]:
                    team_card = QtWidgets.QFrame()
                    team_card.setStyleSheet("""
                        QFrame {
                            background-color: rgba(233, 69, 96, 0.15);
                            border: 2px solid #e94560;
                            border-radius: 8px;
                            padding: 8px 12px;
                        }
                    """)
                    team_card_layout = QtWidgets.QVBoxLayout(team_card)
                    team_card_layout.setContentsMargins(5, 5, 5, 5)
                    
                    teammate_label = QtWidgets.QLabel(teammate)
                    teammate_label.setAlignment(QtCore.Qt.AlignCenter)
                    teammate_label.setStyleSheet("""
                        font-size: 12px;
                        color: #ff6b6b;
                        font-weight: bold;
                    """)
                    team_card_layout.addWidget(teammate_label)
                    
                    self.team_layout.addWidget(team_card)
                self.team_container.setVisible(True)
            else:
                self.team_label.setVisible(False)
                self.team_container.setVisible(False)
        
    def setup_ui(self):
        """Thiết lập giao diện thẻ vai trò"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # User header (username + logout)
        self.user_header = UserHeader(self)
        self.user_header.logout_clicked.connect(self.on_logout)
        main_layout.addWidget(self.user_header)
        
        # Main card container
        card = QtWidgets.QFrame()
        card.setObjectName("role_card")
        card.setStyleSheet("""
            QFrame#role_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 3px solid #e94560;
                border-radius: 15px;
            }
        """)
        
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(20)
        card_layout.setContentsMargins(30, 30, 30, 30)
        
        # Timer ở trên cùng
        self.timer_label = QtWidgets.QLabel(f"⏱️ {self.remaining_time}s")
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        self.timer_label.setStyleSheet("""
            font-size: 18px;
            color: #f39c12;
            font-weight: bold;
            background-color: rgba(243, 156, 18, 0.1);
            padding: 8px;
            border-radius: 5px;
        """)
        card_layout.addWidget(self.timer_label)
        
        # Biểu tượng vai trò 
        self.icon_label = QtWidgets.QLabel("❓")
        self.icon_label.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 120px;")
        card_layout.addWidget(self.icon_label)
        
        # Role
        you_are_label = QtWidgets.QLabel("YOU ARE")
        you_are_label.setAlignment(QtCore.Qt.AlignCenter)
        you_are_label.setStyleSheet("""
            font-size: 16px;
            color: #888888;
            letter-spacing: 3px;
        """)
        card_layout.addWidget(you_are_label)
        self.role_label = QtWidgets.QLabel("UNKNOWN")
        self.role_label.setAlignment(QtCore.Qt.AlignCenter)
        self.role_label.setStyleSheet("""
            font-size: 36px;
            color: #e94560;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        card_layout.addWidget(self.role_label)
        
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("background-color: #444444; max-height: 2px;")
        card_layout.addWidget(line)
        
        # Mô tả vai trò
        description_scroll = QtWidgets.QScrollArea()
        description_scroll.setWidgetResizable(True)
        description_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        description_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 8px;
                background-color: #2a2a3e;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #e94560;
                border-radius: 4px;
            }
        """)
        
        description_text = QtWidgets.QLabel("")
        description_text.setWordWrap(True)
        description_text.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        description_text.setStyleSheet("""
            font-size: 14px;
            color: #cccccc;
            line-height: 1.6;
            padding: 10px;
        """)
        
        self.description_text = description_text
        description_scroll.setWidget(self.description_text)
        card_layout.addWidget(description_scroll)
        
        # Werewolf team (sẽ được update khi có data)
        self.team_label = QtWidgets.QLabel("🐺 Your Werewolf Team:")
        self.team_label.setStyleSheet("""
            font-size: 14px;
            color: #e94560;
            font-weight: bold;
            margin-top: 10px;
        """)
        self.team_label.setVisible(False)
        card_layout.addWidget(self.team_label)
        
        # Tạo các thẻ thành viên đội sói
        self.team_layout = QtWidgets.QHBoxLayout()
        self.team_layout.setSpacing(10)
        
        self.team_container = QtWidgets.QWidget()
        self.team_container.setLayout(self.team_layout)
        self.team_container.setVisible(False)
        card_layout.addWidget(self.team_container)
        
        card_layout.addStretch()
        
        # Ready button - cho phép người chơi ready sớm
        self.ready_button = QtWidgets.QPushButton("✓ Ready")
        self.ready_button.setObjectName("ready_button")
        self.ready_button.setStyleSheet("""
            QPushButton#ready_button {
                background-color: #2ecc71;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 30px;
                border: none;
                border-radius: 8px;
                min-height: 40px;
            }
            QPushButton#ready_button:hover {
                background-color: #27ae60;
            }
            QPushButton#ready_button:pressed {
                background-color: #229954;
            }
        """)
        self.ready_button.clicked.connect(self.on_ready_clicked)
        card_layout.addWidget(self.ready_button)
        
        main_layout.addWidget(card)
        
    def start_timer(self):
        """Bắt đầu bộ đếm thời gian 30 giây"""
        if hasattr(self, 'countdown_timer') and self.countdown_timer:
            self.countdown_timer.stop()
        self.countdown_timer = QtCore.QTimer()
        self.countdown_timer.timeout.connect(self.update_timer)
        self.countdown_timer.start(1000)  # Cập nhật mỗi giây
        # Update UI ngay lập tức
        self.timer_label.setText(f"⏱️ {self.remaining_time}s")
        
    def update_timer(self):
        """Cập nhật bộ đếm thời gian"""
        if self.start_time is None:
            self.countdown_timer.stop()
            return
            
        # Tính remaining_time dựa trên elapsed time thực tế
        elapsed = time.time() - self.start_time
        self.remaining_time = max(0, int(self.total_time - elapsed))
        
        if self.remaining_time > 0:
            self.timer_label.setText(f"⏱️ {self.remaining_time}s")
        else:
            self.timer_label.setText("✓ Time's up!")
            self.timer_label.setStyleSheet("""
                font-size: 18px;
                color: #2ecc71;
                font-weight: bold;
                background-color: rgba(46, 204, 113, 0.1);
                padding: 8px;
                border-radius: 5px;
            """)
            self.countdown_timer.stop()
            # Hết thời gian: gửi ROLE_CARD_DONE_REQ và đợi PHASE_NIGHT từ server (không navigate đến night_begin)
            self.send_timeout_and_wait()
            
    def on_ready_clicked(self):
        """Xử lý khi người chơi click Ready"""
        # Disable button để tránh click nhiều lần
        self.ready_button.setEnabled(False)
        self.ready_button.setText("Ready...")
        # Dừng timer
        if hasattr(self, 'countdown_timer'):
            self.countdown_timer.stop()
        # Ready: gửi ROLE_CARD_DONE_REQ và navigate đến night_begin (logic cũ)
        self.send_ready_and_navigate()
        
    def send_ready_and_navigate(self):
        """Gửi ROLE_CARD_DONE_REQ và navigate đến night_begin window (logic cũ)"""
        elapsed_time = time.time() - self.start_time
        remaining_night_time = max(0, self.total_time - elapsed_time)  # Thời gian còn lại cho night begin
        
        print(f"[DEBUG] Role card ready! Elapsed: {elapsed_time:.1f}s, Remaining night time: {remaining_night_time:.1f}s")
        
        if self.network_client and self.room_id:
            try:
                # Gửi ROLE_CARD_DONE_REQ
                self.network_client.send_packet(310, {"room_id": self.room_id})  # 310 = ROLE_CARD_DONE_REQ
                print(f"[DEBUG] Sent ROLE_CARD_DONE_REQ to server")
            except Exception as e:
                print(f"[ERROR] Failed to notify server ROLE_CARD_DONE_REQ: {e}")
        
        # Navigate đến night_begin window (nếu có WindowManager)
        if self.window_manager:
            self.window_manager.set_shared_data("night_begin_remaining_time", int(remaining_night_time))
            self.window_manager.navigate_to("night_begin")
        
    def send_timeout_and_wait(self):
        """Gửi ROLE_CARD_DONE_REQ khi hết thời gian và đợi PHASE_NIGHT từ server"""
        print(f"[DEBUG] Role card timeout! Sending ROLE_CARD_DONE_REQ and waiting for PHASE_NIGHT")
        
        if self.network_client and self.room_id:
            try:
                # Gửi ROLE_CARD_DONE_REQ
                self.network_client.send_packet(310, {"room_id": self.room_id})  # 310 = ROLE_CARD_DONE_REQ
                print(f"[DEBUG] Sent ROLE_CARD_DONE_REQ to server (timeout)")
            except Exception as e:
                print(f"[ERROR] Failed to notify server ROLE_CARD_DONE_REQ: {e}")
        
        # Không navigate đến night_begin - sẽ đợi PHASE_NIGHT từ server
        # PHASE_NIGHT sẽ được xử lý trong room_window và sẽ start night phase
            
    def closeEvent(self, event):
        """Stop timer when closing"""
        if hasattr(self, 'countdown_timer'):
            self.countdown_timer.stop()
        # Note: ROLE_CARD_DONE_REQ đã được gửi trong send_ready_and_close() hoặc update_timer()
        event.accept()
    
    def on_logout(self):
        """Handle logout button click"""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout? You will leave the game.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                # Send logout request
                if self.network_client:
                    self.network_client.send_packet(105, {})  # LOGOUT_REQ
                if self.toast_manager:
                    self.toast_manager.info("Logging out...")
                
                # Stop timer
                if hasattr(self, 'countdown_timer'):
                    self.countdown_timer.stop()
                
                # Clear shared data
                self.window_manager.set_shared_data("user_id", None)
                self.window_manager.set_shared_data("username", None)
                self.window_manager.set_shared_data("current_room_id", None)
                self.window_manager.set_shared_data("is_host", False)
                self.window_manager.set_shared_data("connected", False)

                # Navigate to welcome screen
                self.window_manager.navigate_to("welcome")

            except Exception as e:
                if self.toast_manager:
                    self.toast_manager.error(f"Logout error: {str(e)}")
