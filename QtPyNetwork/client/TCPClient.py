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
        self.__socket: QAbstractSocket = None

    @Slot(str, int)
    def start(self, ip: str, port: int, timeout: int = 5):
        if self.__socket:
            self._logger.info(f"Closing and connecting to {ip}:{port}")
            self.__socket.close()
            self.__socket = None
            self.__buffer = None

        self.__socket = QTcpSocket()

        self.__buffer = DataBuffer(self.__socket)
        self.__buffer.data.connect(self.on_message)

        self.__socket.connected.connect(self.__on_socket_connected)
        self.__socket.disconnected.connect(self.__on_socket_disconnected)
        self.__socket.error.connect(self.__on_socket_error)
        self.__socket.connectToHost(QHostAddress(ip), port)

        self._logger.debug(f"Connecting to {ip}:{port}")
        self._logger.debug(f"Starting connection timer with timeout {timeout} seconds")
        QTimer.singleShot(timeout * 1000, self.__check_connected)

    @Slot(bytes)
    def write(self, data: bytes):
        if self.__buffer:
            self.__buffer.write(data)

    @Slot()
    def __on_socket_connected(self):
        ip = self.__socket.peerAddress().toString()
        port = int(self.__socket.peerPort())
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
        if self.__socket:
            error = self.__socket.errorString()
            self.error.emit(Exception(error))

    @Slot()
    def __check_connected(self):
        if self.__socket and self.__socket.state() != QAbstractSocket.SocketState.ConnectedState:
            self.__socket.close()
            self.on_failed_to_connect()

    @Slot(int)
    def wait(self, timeout: int = 5):
        """Wait for client to close."""
        timer = QDeadlineTimer(1000 * timeout)
        while not timer.hasExpired():
            if self.__socket.state() != QAbstractSocket.SocketState.ConnectedState:
                break

    @Slot()
    def is_running(self) -> bool:
        return self.__socket is not None and self.__socket.state() == QAbstractSocket.SocketState.ConnectedState

    @Slot()
    def close(self):
        if self.__socket:
            self.__socket.close()
            self.__socket = None
        self.closed.emit()
