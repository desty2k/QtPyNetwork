from qtpy.QtNetwork import QAbstractSocket, QUdpSocket
from qtpy.QtCore import QObject, QTimer, Signal, Slot
from struct import unpack, calcsize, pack

HEADER = '!L'
HEADER_SIZE = calcsize(HEADER)


class DataBuffer(QObject):
    """Small wrapper around QT's QAbstractSocket to make it easier to use.
    Stores data in a buffer and emits signals when data is ready."""

    data = Signal(bytes)

    def __init__(self, socket: QAbstractSocket):
        super().__init__()
        self.__data = b""
        self.__size_left = 0
        self.__socket = socket
        self.__socket.readyRead.connect(self.on_socket_ready_read)

    @Slot()
    def on_socket_ready_read(self) -> None:
        """Read data from socket."""
        while self.__socket.bytesAvailable():
            size_left = self.__size_left
            # print(f"Left: {size_left}")
            if size_left > 0:
                data = self.__socket.read(size_left)
                size_left = size_left - len(data)
                # print(f"ContinueR: {size_left}, {len(data)}")
                if size_left > 0:
                    self.__data += data
                    self.__size_left = size_left
                else:
                    data = self.__data + data
                    self.__data = b""
                    self.__size_left = 0
                    self.data.emit(data)
            else:
                header = self.__socket.read(HEADER_SIZE)
                data_size = unpack(HEADER, header)[0]
                data = self.__socket.read(data_size)
                # print(f"EmptyB: {header}, {data_size}")
                if len(data) < data_size:
                    self.__data = data
                    self.__size_left = data_size - len(data)
                else:
                    self.data.emit(data)

    @Slot(bytes)
    def write(self, data: bytes) -> None:
        """Write data to socket.

        Args:
            data (bytes): Data to write.
        """
        data = pack(HEADER, len(data)) + data
        self.__socket.write(data)
        self.__socket.flush()
