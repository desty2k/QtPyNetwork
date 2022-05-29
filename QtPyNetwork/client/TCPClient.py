from qtpy.QtNetwork import QAbstractSocket, QTcpSocket, QHostAddress
from qtpy.QtCore import Signal, Slot, QTimer, QDeadlineTimer

from QtPyNetwork.common import DataBuffer
from .AbstractClient import AbstractClient

import logging


class TCPClient(AbstractClient):
    def __init__(self):
        super(TCPClient, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        self.__buffer = None

    @Slot(str, int)
    def start(self, ip: str, port: int, timeout: int = 5):
        if self._socket:
            self._logger.info(f"Closing and connecting to {ip}:{port}")
            self._socket.close()
            self._socket = None
            self.__buffer = None

        self._socket = QTcpSocket(self)

        self.__buffer = DataBuffer(self._socket)
        self.__buffer.data.connect(self.on_message)

        self._socket.connected.connect(self.__on_socket_connected)
        self._socket.disconnected.connect(self.__on_socket_disconnected)
        self._socket.error.connect(self.__on_socket_error)
        self._socket.connectToHost(QHostAddress(ip), port)
        self._logger.debug(f"Connecting to {ip}:{port}")
        self._logger.debug(f"Starting connection timer with timeout {timeout} seconds")
        QTimer.singleShot(timeout * 1000, self.__check_connected)
        # self.__check_connected(timeout)

    @Slot(bytes)
    def write(self, data: bytes):
        if self.__buffer:
            self.__buffer.write(data)

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
    def __on_socket_error(self):
        """Handle socket errors.

        Note:
            Emits error signal.
        """
        if self._socket:
            error = self._socket.errorString()
            self.error.emit(Exception(error))

    @Slot()
    def __check_connected(self):
        if self._socket and self._socket.state() != QAbstractSocket.SocketState.ConnectedState:
            self._socket.close()
            self.on_failed_to_connect()

    @Slot(int)
    def wait(self, timeout: int = 5):
        """Wait for client to close."""
        timer = QDeadlineTimer(1000 * timeout)
        while not timer.hasExpired():
            if self._socket.state() != QAbstractSocket.SocketState.ConnectedState:
                break

