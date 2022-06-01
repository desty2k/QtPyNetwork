from qtpy.QtCore import Slot, Signal, QThread, Qt
from .TCPClient import TCPClient
from .AbstractClient import AbstractClient


class _Worker(TCPClient):
    write_signal = Signal(bytes)
    close_signal = Signal()
    start_signal = Signal()

    def __init__(self, ip: str, port: int, timeout: int = 5):
        super().__init__()
        self.__ip = ip
        self.__port = port
        self.__timeout = timeout

        self.write_signal.connect(self.write)
        self.start_signal.connect(self.start)
        self.close_signal.connect(self.close, Qt.BlockingQueuedConnection)

    @Slot()
    def start(self):
        """Worker must be started from its own thread."""
        super(_Worker, self).start(self.__ip, self.__port, self.__timeout)


class ThreadedTCPClient(AbstractClient):

    def __init__(self):
        super().__init__()
        self.__worker: _Worker = None
        self.__thread: QThread = None

    @Slot(str, int)
    def start(self, ip: str, port: int, timeout: int = 5):
        if self.is_running():
            self.close()

        self.__worker = _Worker(ip, port, timeout)
        self.__worker.message.connect(self.on_message)
        self.__worker.connected.connect(self.on_connected)
        self.__worker.failed_to_connect.connect(self.on_failed_to_connect)
        self.__worker.disconnected.connect(self.on_disconnected)
        self.__worker.closed.connect(self.on_closed)
        self.__worker.error.connect(self.on_error)
        self.__thread = QThread()
        self.__worker.moveToThread(self.__thread)
        self.__thread.started.connect(self.__worker.start_signal.emit)
        self.__thread.start()

    @Slot(Exception)
    def on_error(self, error: Exception):
        self.error.emit(error)

    @Slot(bytes)
    def write(self, data: bytes):
        self.__worker.write_signal.emit(data)

    @Slot()
    def is_running(self) -> bytes:
        return (self.__worker is not None and self.__worker.is_running()
                and self.__thread is not None and self.__thread.isRunning())

    @Slot(int)
    def wait(self, timeout: int = 5):
        if self.__worker is not None and self.__thread is not None:
            self.__worker.wait(timeout)
            self.__thread.wait(timeout)

    @Slot()
    def close(self):
        if self.__worker is not None and self.__thread is not None:
            self.__worker.close_signal.emit()
            self.__thread.quit()
