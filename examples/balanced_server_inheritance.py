from qtpy.QtCore import Slot, QCoreApplication

import sys
import logging
import traceback

from QtPyNetwork.server import QBalancedServer
from QtPyNetwork.models import Device

IP, PORT = "127.0.0.1", 12500


class Main(QBalancedServer):

    def __init__(self):
        super(Main, self).__init__(None)
        self.logger = logging.getLogger(self.__class__.__name__)

    @Slot(Device, str, int)
    def on_connected(self, device: Device, ip, port):
        self.logger.info("New device connected: {}".format(device.id()))

    @Slot(Device, bytes)
    def on_message(self, device: Device, message: bytes):
        self.logger.info("Received from {}: {}".format(device.id(), message))

    @Slot(Device)
    def on_disconnected(self, device: Device):
        self.logger.info("Device {} disconnected".format(device.id()))
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
