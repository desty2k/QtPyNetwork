from qtpy.QtCore import Slot, Signal
from qtpy.QtNetwork import QTcpServer, QHostAddress, QTcpSocket

from .AbstractServer import AbstractServer


class _TCPServer(QTcpServer):
    """Listens for incoming connections."""
    incomming_connection = Signal(int)

    def __init__(self, parent=None):
        super(_TCPServer, self).__init__(parent)

    @Slot(int)
    def incomingConnection(self, socket_descriptor):
        self.incomming_connection.emit(int(socket_descriptor))


class TCPServer(AbstractServer):
    def __init__(self, balancer):
        super(TCPServer, self).__init__(balancer)
        self.server = _TCPServer()
        self.server.incomming_connection.connect(self.on_incomming_connection)

    @Slot(int)
    def on_incomming_connection(self, socket_descriptor: int):
        self.balancer.balance(QTcpSocket, socket_descriptor)

    @Slot(str, int)
    def start(self, ip: str, port: int):
        ip = QHostAddress(ip)
        self.server.listen(ip, port)

    @Slot()
    def close(self):
        self.server.close()

    @Slot()
    def is_running(self) -> bool:
        return self.server.isListening() and self.balancer.is_running()

    @Slot()
    def wait(self):
        return self.balancer.wait()
