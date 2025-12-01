from PyQt5 import QtWidgets, QtCore, QtGui
class RoleCardWindow(QtWidgets.QDialog):
    """Window hiển thị role card với timer 30s"""
    
    def __init__(self, role_data, parent=None):
        super().__init__(parent)
        self.role_data = role_data
        self.remaining_time = 30
        
        self.setObjectName("role_card_window")
        self.setModal(True)
        self.setWindowTitle("Your Role")
        self.setFixedSize(500, 600)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        
        self.setup_ui()
        self.start_timer()
        
    def setup_ui(self):
        """Thiết lập giao diện thẻ vai trò"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
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
        icon_label = QtWidgets.QLabel(self.role_data.get("role_icon", "❓"))
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 120px;")
        card_layout.addWidget(icon_label)
        
        # Role
        you_are_label = QtWidgets.QLabel("YOU ARE")
        you_are_label.setAlignment(QtCore.Qt.AlignCenter)
        you_are_label.setStyleSheet("""
            font-size: 16px;
            color: #888888;
            letter-spacing: 3px;
        """)
        card_layout.addWidget(you_are_label)
        role_name = self.role_data.get("role_name", "Unknown")
        role_label = QtWidgets.QLabel(role_name.upper())
        role_label.setAlignment(QtCore.Qt.AlignCenter)
        role_label.setStyleSheet("""
            font-size: 36px;
            color: #e94560;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        card_layout.addWidget(role_label)
        
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
        
        description_text = QtWidgets.QLabel(self.role_data.get("role_description", ""))
        description_text.setWordWrap(True)
        description_text.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        description_text.setStyleSheet("""
            font-size: 14px;
            color: #cccccc;
            line-height: 1.6;
            padding: 10px;
        """)
        
        description_scroll.setWidget(description_text)
        card_layout.addWidget(description_scroll)
        
        # Nếu là sói -> hiển thị đội sói
        if "werewolf_team" in self.role_data and self.role_data["werewolf_team"]:
            team_label = QtWidgets.QLabel("🐺 Your Werewolf Team:")
            team_label.setStyleSheet("""
                font-size: 14px;
                color: #e94560;
                font-weight: bold;
                margin-top: 10px;
            """)
            card_layout.addWidget(team_label)
            
            # Tạo các thẻ thành viên đội sói
            team_layout = QtWidgets.QHBoxLayout()
            team_layout.setSpacing(10)
            
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
                
                team_layout.addWidget(team_card)
            
            team_container = QtWidgets.QWidget()
            team_container.setLayout(team_layout)
            card_layout.addWidget(team_container)
        
        card_layout.addStretch()
        
        # Close button (ẩn đi, vì tự động close sau 30s)
        # self.close_button = QtWidgets.QPushButton("Please wait...")
        # self.close_button.setObjectName("close_button")
        # ... button code hidden ...
        # card_layout.addWidget(self.close_button)
        
        main_layout.addWidget(card)
        
    def start_timer(self):
        """Bắt đầu bộ đếm thời gian 30 giây"""
        self.countdown_timer = QtCore.QTimer()
        self.countdown_timer.timeout.connect(self.update_timer)
        self.countdown_timer.start(1000)  # Cập nhật mỗi giây
        
    def update_timer(self):
        """Cập nhật bộ đếm thời gian"""
        self.remaining_time -= 1
        
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
            # Tự động đóng dialog sau 30s
            self.accept()
            
    def closeEvent(self, event):
        """Stop timer when closing"""
        if hasattr(self, 'countdown_timer'):
            self.countdown_timer.stop()
        event.accept()
