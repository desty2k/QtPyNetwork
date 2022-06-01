from qtpy.QtCore import Slot, QCoreApplication

import sys
import logging
import traceback

from QtPyNetwork.server import TCPServer
from QtPyNetwork.balancer import ThreadPoolBalancer
from QtPyNetwork.model import Client

IP, PORT = "127.0.0.1", 12500


class Main(TCPServer):

    def __init__(self):
        super(Main, self).__init__(ThreadPoolBalancer(threads=4))
        self.logger = logging.getLogger(self.__class__.__name__)

    @Slot(Client, str, int)
    def on_connected(self, client: Client, ip, port):
        self.logger.info("New client connected: {}".format(client.id()))

    @Slot(Client, bytes)
    def on_message(self, client: Client, message: bytes):
        self.logger.info("Received from {}: {}".format(client.id(), message))

    @Slot(Client)
    def on_disconnected(self, client: Client):
        self.logger.info("Device {} disconnected".format(client.id()))
        self.close()


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
    main.start(IP, PORT)
    sys.exit(app.exec_())
