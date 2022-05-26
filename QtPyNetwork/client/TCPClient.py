from qtpy.QtNetwork import QAbstractSocket, QTcpSocket, QHostAddress
from qtpy.QtCore import Signal, Slot, QTimer

from QtPyNetwork.common import read, write
from .AbstractClient import AbstractClient

import logging


class TCPClient(AbstractClient):
    def __init__(self, timeout: int = 2):
        super(TCPClient, self).__init__(timeout)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._data = b""
        self._size_left = 0

    @Slot(str, int)
    def start(self, ip: str, port: int):
        self._socket = QTcpSocket(self)
        self._socket.connected.connect(self.__on_socket_connected)
        self._socket.disconnected.connect(self.__on_socket_disconnected)
        self._socket.readyRead.connect(self.__on_socket_ready_read)
        self._socket.error.connect(self.__on_socket_error)
        self._socket.connectToHost(QHostAddress(ip), port)
        self._logger.debug(f"Connecting to {ip}:{port}")
        QTimer.singleShot(self._timeout * 1000, self.__check_connected)
        self._logger.debug(f"Started connection timer with timeout {self._timeout} seconds")

    @Slot(bytes)
    def write(self, data: bytes):
        if self._socket.state() == QAbstractSocket.ConnectedState:
            write(self._socket, data)

    @Slot()
    def __on_socket_connected(self):
        ip = self._socket.peerAddress().toString()
        port = int(self._socket.peerPort())
        self._logger.info("Connected to {}:{}".format(ip, port))
        self.on_connected(ip, port)

    @Slot()
    def __on_socket_disconnected(self):
        self._logger.info("Disconnected from server")
        self.on_disconnected()

    @Slot()
    def __on_socket_ready_read(self):
        data, size_left = read(self._socket, self._data, self._size_left)
        print(f"TCPClient left: {size_left}, received: {data}")
        if size_left == 0:
            self._size_left = 0
            self._data = b""
            self.on_message(data)
        else:
            self._data = data
            self._size_left = size_left

    @Slot()
    def __on_socket_error(self):
        """Handle socket errors.

        Note:
            Emits error signal.
        """
        error = self._socket.errorString()
        self.error.emit(Exception(error))

    def __check_connected(self):
        if not self._socket.state() == QAbstractSocket.ConnectedState:
            self._socket.close()
            self.on_failed_to_connect()
