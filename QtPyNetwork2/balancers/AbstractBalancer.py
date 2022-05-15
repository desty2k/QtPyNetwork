from qtpy.QtCore import QObject, Signal, Slot

import logging
from struct import calcsize

HEADER = '!L'
HEADER_SIZE = calcsize(HEADER)


class AbstractBalancer(QObject):
    disconnected = Signal(int)
    connected = Signal(int, str, int)
    message = Signal(int, bytes)
    error = Signal(int, Exception)
    closed = Signal()

    def __init__(self):
        super(AbstractBalancer, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__socket_id = 0

    @Slot(type, int)
    def balance(self, socket_type: type, socket_descriptor: int):
        pass

    @Slot(int, bytes)
    def write(self, device_id: int, message: bytes):
        pass

    @Slot(int)
    def close(self, device_id: int):
        pass

    @Slot()
    def get_next_socket_id(self) -> int:
        self.__socket_id += 1
        return self.__socket_id
