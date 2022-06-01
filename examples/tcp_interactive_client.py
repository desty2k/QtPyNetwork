from qtpy.QtWidgets import QApplication, QDialog, QPushButton, QVBoxLayout, QTextEdit
from qtpy.QtCore import QObject, Slot, Signal

import sys
import logging

from QtPyNetwork.client import TCPClient

IP = "127.0.0.1"
PORT = 12500


class MainWindow(QDialog):
    send_text = Signal(bytes)

    def __init__(self):
        super().__init__(None)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.text_widget = QTextEdit(self)
        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.on_send_button_clicked)

        self.connect_button = QPushButton("Connect", self)
        self.disconnect_button = QPushButton("Disconnect", self)
        self.close_button = QPushButton("Close", self)

        self.layout.addWidget(self.text_widget)
        self.layout.addWidget(self.connect_button)
        self.layout.addWidget(self.send_button)
        self.layout.addWidget(self.disconnect_button)
        self.layout.addWidget(self.close_button)

    @Slot()
    def on_send_button_clicked(self):
        text = self.text_widget.toPlainText()
        text = text.encode()
        self.send_text.emit(text)
        self.text_widget.clear()


class Main(QObject):

    def __init__(self):
        super(Main, self).__init__(None)
        self.logger = logging.getLogger(self.__class__.__name__)

        self.client = TCPClient()
        self.client.message.connect(self.on_message)
        self.client.connected.connect(self.on_connected)
        self.client.failed_to_connect.connect(self.on_failed_to_connect)

        self.main_window = MainWindow()
        self.main_window.send_text.connect(self.client.write)
        self.main_window.connect_button.clicked.connect(self.start)
        self.main_window.disconnect_button.clicked.connect(self.client.close)
        self.main_window.close_button.clicked.connect(self.close)

    @Slot()
    def start(self):
        self.client.start(IP, PORT, timeout=5)
        self.main_window.show()

    @Slot(str, int)
    def on_connected(self, ip: str, port: int):
        self.client.write(b"Kick me plz")

    @Slot(bytes)
    def on_message(self, data: bytes):
        self.logger.info(f"Received: {data}")

    @Slot()
    def on_failed_to_connect(self):
        self.logger.error("Failed to connect")

    @Slot()
    def close(self):
        self.client.close()
        self.client.wait()
        self.main_window.close()
        QApplication.instance().quit()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.NOTSET,
        format="%(asctime)s [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()])
    logging.getLogger().debug("Logger enabled")

    app = QApplication(sys.argv)

    main = Main()
    main.start()
    sys.exit(app.exec_())
