from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Slot, QCoreApplication

import sys
import logging
import traceback

from QtPyNetwork.server import TCPServer
from QtPyNetwork.balancer import ThreadPoolBalancer
from QtPyNetwork.model import Client

IP = "127.0.0.1"
PORT = 12500


class Main(QObject):

    def __init__(self):
        super(Main, self).__init__(None)
        self.logger = logging.getLogger(self.__class__.__name__)

        self.server = TCPServer(ThreadPoolBalancer(threads=8))
        self.server.connected.connect(self.on_connected)
        self.server.disconnected.connect(self.on_disconnected)
        self.server.message.connect(self.on_message)

    @Slot()
    def setup(self):
        self.server.start(IP, PORT)

    @Slot(Client, str, int)
    def on_connected(self, client: Client, ip: str, port: int):
        for i in range(10):
            client.write(f"Hello {i}".encode())

    @Slot(Client, bytes)
    def on_message(self, client: Client, message: bytes):
        self.logger.info("Received {}: {}".format(client.id(), message))
        # if message.decode() == "Kick me plz":
        #     client.disconnect()

    @Slot(Client)
    def on_disconnected(self, client: Client):
        self.logger.info("Disconnected: {}; Connected: {}".format(client.id(), client.is_connected()))
        # self.close()

    @Slot()
    def close(self):
        self.server.close()
        while self.server.is_running():
            self.server.wait()
        QApplication.instance().quit()


if __name__ == '__main__':
    sys._excepthook = sys.excepthook
    def exception_hook(exctype, value, tb):
        logging.critical(''.join(traceback.format_exception(exctype, value, tb)))
        sys._excepthook(exctype, value, tb)
        sys.exit(1)
    sys.excepthook = exception_hook

    logging.basicConfig(
        level=logging.NOTSET,
        format="%(asctime)s [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()])
    logging.getLogger().debug("Logger enabled")
    app = QCoreApplication(sys.argv)

    main = Main()
    main.setup()
    sys.exit(app.exec_())
