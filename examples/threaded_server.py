from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QObject, Slot, QCoreApplication

import sys
import logging

from QtPyNetwork.server import QThreadedServer

IP = "127.0.0.1"
PORT = 7890
KEY = b""


class Main(QObject):

    def __init__(self):
        super(Main, self).__init__(None)

    def setup(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.srv = QThreadedServer()
        self.srv.disconnected.connect(self.close)
        self.srv.connected.connect(lambda device_id, ip, port: self.srv.writeAll({"id": device_id,
                                                                                  "ip": ip,
                                                                                  "port": port,
                                                                                  "data": "Hello world!"}))
        self.srv.start(IP, PORT, KEY)

    @Slot()
    def close(self):
        self.srv.close()
        while self.srv.isRunning():
            self.srv.wait()
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
