# Code để check UI mà không phải chạy server
# Night phase
import sys
import os
# Ensure project src root is on sys.path so package imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt5 import QtWidgets
from windows.night_begin_window import NightBeginWindow
from utils.image_utils import create_image_icon_label
from windows.roles.seer.seer_select_window import SeerSelectWindow
from windows.roles.seer.seer_wait_window import SeerWaitWindow
from windows.roles.seer.seer_result_window import SeerResultWindow
# Guard
from windows.roles.guard.guard_select_window import GuardSelectWindow
from windows.roles.guard.guard_wait_window import GuardWaitWindow
# Wolf
from windows.roles.wolf.wolf_select_window import WolfSelectWindow
from windows.roles.wolf.wolf_chat_window import WolfChatWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Chọn window muốn test ở đây:
    # 1. NightBeginWindow
    # night = NightBeginWindow(duration_seconds=8)
    # night.show()

    # 2. SeerSelectWindow
    # players = [
    #     {"username": "Alice"},
    #     {"username": "Bob"},
    #     {"username": "Charlie"},
    #     {"username": "David"},
    # ]
    # my_username = "Alice"
    # seer_select = SeerSelectWindow(players, my_username, duration_seconds=15)
    # seer_select.show()

    # 3. SeerWaitWindow
    # seer_wait = SeerWaitWindow(duration_seconds=12)
    # seer_wait.show()


    # 4. SeerResultWindow
    # seer_result = SeerResultWindow("Bob", is_werewolf=True)
    # seer_result.show()


    # 5. GuardSelectWindow
    # players = [
    #     {"username": "Alice"},
    #     {"username": "Bob"},
    #     {"username": "Charlie"},
    #     {"username": "David"},
    # ]
    # my_username = "Alice"
    # guard_select = GuardSelectWindow(players, my_username, duration_seconds=15)
    # guard_select.show()

    # 6. GuardWaitWindow
    # guard_wait = GuardWaitWindow(duration_seconds=12)
    # guard_wait.show()

    # 7. WolfSelectWindow
    players = [
        {"username": "Alice"},
        {"username": "Bob"},
        {"username": "Charlie"},
        {"username": "David"},
    ]
    alive_status = [1, 1, 0, 1]
    wolf_select = WolfSelectWindow([p["username"] for p in players], alive_status)
    wolf_select.show()

    # 8. WolfChatWindow
    # wolf_chat = WolfChatWindow("Alice", ["Alice", "David"])
    # wolf_chat.show()

    # 9. (Removed) WolfPhaseController - night_phase_controller now manages wolf vote/chat directly
    # wolf_phase.show()

    sys.exit(app.exec_())
