from qtpy.QtCore import QObject, Signal, Slot
from abc import ABC, abstractmethod

import logging
from struct import calcsize

HEADER = '!L'
HEADER_SIZE = calcsize(HEADER)


class AbstractBalancer(QObject):
    disconnected = Signal(int)
    connected = Signal(int, str, int)
    message = Signal(int, bytes)
    client_error = Signal(int, Exception)
    closed = Signal()

    def __init__(self):
        super(AbstractBalancer, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__socket_id = 0

    @abstractmethod
    @Slot(type, int)
    def balance(self, socket_type: type, socket_descriptor: int) -> int:
        pass

    @abstractmethod
    @Slot(int, bytes)
    def write(self, client_id: int, message: bytes):
        pass

    @abstractmethod
    @Slot(bytes)
    def write_all(self, message: bytes):
        pass

    @abstractmethod
    @Slot(int)
    def disconnect(self, client_id: int):
        pass

    @abstractmethod
    @Slot()
    def close(self) -> None:
        pass

    @abstractmethod
    @Slot()
    def is_running(self) -> bool:
        pass

    @abstractmethod
    @Slot()
    def wait(self) -> None:
        pass

    @Slot()
    def get_next_socket_id(self) -> int:
        self.__socket_id += 1
        return self.__socket_id
