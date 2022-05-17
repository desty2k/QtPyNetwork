from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Slot, QCoreApplication

import sys
import logging

from QtPyNetwork.client import QThreadedClient

IP = "127.0.0.1"
PORT = 12500


class Main(QObject):

    def __init__(self):
        super(Main, self).__init__(None)

    def setup(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.cln = QThreadedClient()
        self.cln.message.connect(self.on_message)
        self.cln.connected.connect(self.on_connected)
        self.cln.failed_to_connect.connect(self.close)
        self.cln.disconnected.connect(self.close)
        self.cln.start(IP, PORT)

    @Slot(str, int)
    def on_connected(self, ip: str, port: int):
        self.logger.info(f"Connected to {ip}:{port}")
        self.cln.write(b"Kick me plz")

    @Slot(bytes)
    def on_message(self, data: bytes):
        self.logger.info(f"Received: {data}")

    @Slot()
    def close(self):
        self.cln.close()
        while self.cln.is_running():
            self.cln.wait()
        QApplication.instance().quit()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.NOTSET,
        format="%(asctime)s [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()])
    logging.getLogger().debug("Logger enabled")

    app = QCoreApplication(sys.argv)

    main = Main()
    main.setup()
    sys.exit(app.exec_())
