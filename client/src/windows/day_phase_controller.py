from PyQt5 import QtCore

class DayPhaseController:
    """Manages day phase state, including shared timer for day chat and day vote"""
    
    def __init__(self, window_manager, duration_seconds):
        self.window_manager = window_manager
        self.duration_seconds = duration_seconds
        self.deadline = None
        self.timer = None
        
        # Calculate deadline
        import time
        self.deadline = time.time() + duration_seconds
        
        # Store deadline in shared data
        self.window_manager.set_shared_data("day_vote_deadline", self.deadline)
        
        print(f"[DEBUG] DayPhaseController initialized - duration: {duration_seconds}s, deadline: {self.deadline}")
        
        # Start timer to update both windows
        self.start_timer()
    
    def start_timer(self):
        """Start timer to update remaining time"""
        if self.timer:
            self.timer.stop()
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(1000)  # 1 second interval
    
    def _update_timer(self):
        """Update timer - called every second"""
        import time
        remaining = max(0, int(self.deadline - time.time()))
        
        # Update shared data
        self.window_manager.set_shared_data("day_remaining_time", remaining)
        
        # Update day vote window if visible
        if "day_vote" in self.window_manager.windows:
            day_vote_window = self.window_manager.windows["day_vote"]
            if day_vote_window.isVisible() and hasattr(day_vote_window, 'remaining_time'):
                day_vote_window.remaining_time = remaining
                day_vote_window.timer_label.setText(f"⏱️ {remaining}s")
        
        # Update day chat window if visible (optional - add timer display to day chat)
        if "day_chat" in self.window_manager.windows:
            day_chat_window = self.window_manager.windows["day_chat"]
            if day_chat_window.isVisible() and hasattr(day_chat_window, 'timer_label'):
                day_chat_window.timer_label.setText(f"⏱️ {remaining}s")
        
        # Stop timer when time is up
        if remaining <= 0:
            if self.timer:
                self.timer.stop()
            print("[DEBUG] Day phase timer expired")
    
    def stop(self):
        """Stop the timer"""
        if self.timer:
            self.timer.stop()
            self.timer = None
