from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Slot, QCoreApplication

import sys
import logging
import traceback

from QtPyNetwork.server import TCPServer
from QtPyNetwork.balancer import ThreadPoolBalancer
from QtPyNetwork.models import Device

IP = "127.0.0.1"
PORT = 12500


class Main(QObject):

    def __init__(self):
        super(Main, self).__init__(None)
        self.logger = logging.getLogger(self.__class__.__name__)

        self.balancer = ThreadPoolBalancer(threads=8)
        self.server = TCPServer(self.balancer)
        self.server.connected.connect(lambda device, ip, port: device.write(b"Some important data"))
        self.server.disconnected.connect(self.on_disconnected)
        self.server.message.connect(self.on_message)

    def setup(self):
        self.server.start(IP, PORT)

    @Slot(Device, bytes)
    def on_message(self, device, message: bytes):
        self.logger.info("Received {}: {}".format(device.id(), message))
        if message.decode() == "Kick me plz":
            device.kick()

    @Slot(Device)
    def on_disconnected(self, device):
        self.logger.info("Disconnected: {}; Connected: {}".format(device.id(), device.is_connected()))
        self.close()

    @Slot()
    def close(self):
        self.srv.close()
        while self.srv.is_running():
            self.srv.wait()
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
