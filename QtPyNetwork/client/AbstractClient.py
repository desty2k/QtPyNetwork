from qtpy.QtCore import Slot, Signal, QObject
from qtpy.QtNetwork import QAbstractSocket

from abc import abstractmethod


class AbstractClient(QObject):

    connected = Signal(str, int)
    disconnected = Signal()
    message = Signal(bytes)
    error = Signal(Exception)
    closed = Signal()
    failed_to_connect = Signal()

    def __init__(self):
        super(AbstractClient, self).__init__()

    @abstractmethod
    @Slot(str, int)
    def start(self, ip: str, port: int, timeout: int = 5):
        """Start client thread and connect to server."""
        pass

    @abstractmethod
    @Slot(bytes)
    def write(self, data: bytes):
        """Write data to server.

        Args:
            data (bytes): Data to write.
        """
        pass

    @Slot(str, int)
    def on_connected(self, ip, port):
        """Called when client connects to server.
        Emits connected signal.

        Args:
            ip (str): Client ip address.
            port (int): Client port.
        """
        self.connected.emit(ip, port)

    @Slot(bytes)
    def on_message(self, message: bytes):
        """Called when client receives message from server.
        Emits message signal.

        Args:
            message (bytes): Message.
        """
        self.message.emit(message)

    @Slot()
    def on_disconnected(self):
        """Called when device disconnects from server.
        Emits disconnected signal."""
        self.disconnected.emit()

    @Slot(str)
    def on_error(self, error: str):
        """Called when a socket error occurs.
        Emits error signal.

        Args:
            error (str): Error string.
        """
        self.error.emit(Exception, error)

    @Slot()
    def on_failed_to_connect(self):
        """Called when client fails to connect to server.
        Emits failed_to_connect signal.
        """
        self.failed_to_connect.emit()

    @Slot()
    def on_closed(self):
        """Called when the socket is closed.
        Emits closed signal."""
        self.closed.emit()

    @abstractmethod
    @Slot()
    def close(self):
        """Disconnect from server and close socket."""
        pass

    @abstractmethod
    @Slot()
    def wait(self):
        pass

    @abstractmethod
    @Slot()
    def is_running(self) -> bool:
        """Check if client is running."""
        pass
