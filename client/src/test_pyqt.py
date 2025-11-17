import sys
import socket
from PyQt5 import QtWidgets, QtCore

class ClientWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.sock = None
        self.init_ui()
        self.recv_timer = QtCore.QTimer()
        self.recv_timer.timeout.connect(self.receive_packet)

    def init_ui(self):
        self.setWindowTitle("PyQt TCP Client")
        self.resize(400, 300)

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)

        self.input = QtWidgets.QLineEdit()
        self.input.setPlaceholderText("Nhập payload JSON...")

        self.btn_connect = QtWidgets.QPushButton("Connect")
        self.btn_send = QtWidgets.QPushButton("Send Header 101")
        self.btn_send.setEnabled(False)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.log)
        layout.addWidget(self.input)
        layout.addWidget(self.btn_connect)
        layout.addWidget(self.btn_send)
        self.setLayout(layout)

        self.btn_connect.clicked.connect(self.connect_server)
        self.btn_send.clicked.connect(self.send_test)

    def connect_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", 5000))
        self.log.append("Connected to server")

        self.btn_connect.setEnabled(False)
        self.btn_send.setEnabled(True)

        self.recv_timer.start(50)

    def send_packet(self, header, payload):
        if not self.sock:
            return

        payload_bytes = payload.encode()
        packet = (
            header.to_bytes(2, "big") +
            len(payload_bytes).to_bytes(4, "big") +
            payload_bytes
        )

        self.sock.sendall(packet)
        self.log.append(f"Sent: header={header}, payload={payload}")

    def send_test(self):
        payload = self.input.text()
        if not payload:
            payload = "{\"msg\":\"hello\"}"
        self.send_packet(101, payload)

    def receive_packet(self):
        try:
            self.sock.setblocking(False)
            header_bytes = self.sock.recv(2)
            if not header_bytes:
                return

            header = int.from_bytes(header_bytes, "big")

            length_bytes = self.sock.recv(4)
            length = int.from_bytes(length_bytes, "big")

            payload = self.sock.recv(length).decode()

            self.log.append(f"<b>Received header={header}</b>\n{payload}\n")

        except BlockingIOError:
            pass


app = QtWidgets.QApplication(sys.argv)
win = ClientWindow()
win.show()
sys.exit(app.exec_())
