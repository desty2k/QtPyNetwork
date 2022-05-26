from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Slot, QCoreApplication

import sys
import logging
import traceback

from QtPyNetwork.server import TCPServer
from QtPyNetwork.balancer import NoBalancer
from QtPyNetwork.models import Client

IP = "127.0.0.1"
PORT = 12500


class Main(QObject):

    def __init__(self):
        super(Main, self).__init__(None)
        self.logger = logging.getLogger(self.__class__.__name__)

        self.server = TCPServer(NoBalancer())
        self.server.connected.connect(self.on_client_connected)
        self.server.disconnected.connect(lambda client: print(f"Client disconnected: {client.id()}"))
        self.server.message.connect(lambda client, data: print(f"Received data from client {client.id()}: {data}"))
        # self.server.disconnected.connect(self.on_disconnected)
        # self.server.message.connect(self.on_message)

    @Slot()
    def start(self):
        self.server.start(IP, PORT)

    @Slot(Client, str, int)
    def on_client_connected(self, client, ip, port):
        print(f"Hello new client! {client.id()} - {ip}:{port}")
        client.write(b"Hello from server")

    # @Slot(Device, bytes)
    # def on_message(self, device, message: bytes):
    #     self.logger.info("Received {}: {}".format(device.id(), message))
    #     if message.decode() == "Kick me plz":
    #         device.kick()
    #
    # @Slot(Device)
    # def on_disconnected(self, device):
    #     self.logger.info("Disconnected: {}; Connected: {}".format(device.id(), device.is_connected()))
    #     self.close()

    # @Slot()
    # def close(self):
    #     self.srv.close()
    #     while self.srv.is_running():
    #         self.srv.wait()
    #     QApplication.instance().quit()


if __name__ == '__main__':
    sys._excepthook = sys.excepthook
    def exception_hook(exctype, value, tb):
        # logging.critical(''.join(traceback.format_exception(exctype, value, tb)))
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
    main.start()
    sys.exit(app.exec_())
