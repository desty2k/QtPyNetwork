from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Slot, QCoreApplication

import sys
import logging

from QtPyNetwork.client import TCPClient

IP = "127.0.0.1"
PORT = 12500


class Main(QObject):

    def __init__(self):
        super(Main, self).__init__(None)
        self.logger = logging.getLogger(self.__class__.__name__)

        self.client = TCPClient()
        self.client.message.connect(self.on_message)
        self.client.connected.connect(self.on_connected)
        self.client.failed_to_connect.connect(self.on_failed_to_connect)
        self.client.disconnected.connect(self.close)

    @Slot()
    def start(self):
        self.client.start(IP, PORT)

    @Slot(str, int)
    def on_connected(self, ip: str, port: int):
        self.logger.info(f"Connected to {ip}:{port}")
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
        QApplication.instance().quit()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.NOTSET,
        format="%(asctime)s [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()])
    logging.getLogger().debug("Logger enabled")

    app = QCoreApplication(sys.argv)
    main = Main()
    main.start()
    sys.exit(app.exec_())
