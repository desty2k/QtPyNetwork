from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Slot, QCoreApplication

import sys
import logging
import traceback

from QtPyNetwork.server import TCPServer
from QtPyNetwork.balancer import ThreadBalancer
from QtPyNetwork.model import Client

IP = "127.0.0.1"
PORT = 12500


class Main(QObject):

    def __init__(self):
        super(Main, self).__init__(None)
        self.logger = logging.getLogger(self.__class__.__name__)

        self.server = TCPServer(ThreadBalancer())
        self.server.connected.connect(lambda device, ip, port: device.write(b"Some important data"))
        self.server.disconnected.connect(self.on_disconnected)
        self.server.message.connect(self.on_message)
        self.server.start(IP, PORT)

    @Slot(Client, bytes)
    def on_message(self, client: Client, message: bytes):
        self.logger.info("Received {}: {}".format(client.id(), message))
        if message.decode() == "Kick me plz":
            data = b"Some data"
            # client.write(b"I'm kicked")
            for i in range(20):
                client.write(data)
                data += data

    @Slot(Client)
    def on_disconnected(self, device):
        self.logger.info("Disconnected: {}; Connected: {}".format(device.id(), device.is_connected()))

    @Slot()
    def close(self):
        self.server.close()
        while self.server.is_running():
            self.server.wait()
        QApplication.instance().quit()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.NOTSET,
        format="%(asctime)s [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()])
    logging.getLogger().debug("Logger enabled")

    sys._excepthook = sys.excepthook
    def exception_hook(exctype, value, tb):
        logging.critical(''.join(traceback.format_exception(exctype, value, tb)))
        sys._excepthook(exctype, value, tb)
        sys.exit(1)
    sys.excepthook = exception_hook

    app = QCoreApplication(sys.argv)

    main = Main()
    sys.exit(app.exec_())
