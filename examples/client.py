from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Slot, QCoreApplication

import sys
import logging

from QtPyNetwork.client import QThreadedClient

IP = "127.0.0.1"
PORT = 7890
KEY = b""


class Main(QObject):

    def __init__(self):
        super(Main, self).__init__(None)

    def setup(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.cln = QThreadedClient()
        self.cln.message.connect(self.client_data_received)
        self.cln.failed_to_connect.connect(self.close)
        self.cln.disconnected.connect(self.close)
        self.cln.start(IP, PORT, KEY)

    @Slot(dict)
    def client_data_received(self, data: dict):
        if data.get("data") == "Hello world!":
            self.logger.info("Received Hello world!, closing client!")
            self.close()

    @Slot()
    def close(self):
        self.cln.close()
        while self.cln.isRunning():
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
