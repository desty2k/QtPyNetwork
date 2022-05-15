from qtpy.QtCore import Slot, Signal, QObject, QThread
from qtpy.QtNetwork import QAbstractSocket, QUdpSocket

import logging
from struct import unpack, calcsize

from .AbstractBalancer import AbstractBalancer


class _Worker(QObject):
    disconnected = Signal()
    connected = Signal(str, int)
    readyRead = Signal(bytes)
    error = Signal(Exception)
    closed = Signal()

    close_signal = Signal()

    write = Signal(bytes)

    def __init__(self, client_id, socket_type: type, socket_descriptor: int):
        super(_Worker, self).__init__()
        self.logger = logging.getLogger(f"ThreadBalancerWorker-{client_id}")
        self.socket: QAbstractSocket = None
        self.client_id = client_id
        self.socket_type = socket_type
        self.socket_descriptor = socket_descriptor

    @Slot()
    def start(self):
        socket: QAbstractSocket = self.socket_type()
        socket.setParent(None)
        if socket.setSocketDescriptor(self.socket_descriptor):
            socket.readyRead.connect(self.__on_socket_ready_read)
            socket.disconnected.connect(self.__on_socket_disconnected)
            socket.error.connect(self.__on_socket_error)
            socket.setObjectName(str(self.client_id))
            self.socket = socket
            self.logger.debug(f"New client - {socket.objectName()} - "
                              f"{socket.peerAddress().toString()} - {socket.peerPort()}")
            self.connected.emit(int(socket.objectName()), socket.peerAddress().toString(), socket.peerPort())

    @Slot()
    def __on_socket_ready_read(self):
        """Handle socket messages.

        Note:
            Emits message signal.
        """

        while self.socket.bytesAvailable():
            if self.client_id in self.data:
                size_left = self.data.get(client_id).get("size_left")
                data = socket.read(size_left)
                size_left = size_left - len(data)
                if size_left > 0:
                    self.data[client_id]["size_left"] = size_left
                    self.data[client_id]["data"] += data
                else:
                    data = self.data.get(client_id).get("data") + data
                    del self.data[client_id]
                    self.message.emit(client_id, data)

            else:
                header = socket.read(HEADER_SIZE)
                data_size = unpack(HEADER, header)[0]
                message = socket.read(data_size)

                if len(message) < data_size:
                    data_size = data_size - len(message)
                    self.data[client_id] = {"data": message, "size_left": data_size}
                else:
                    self.message.emit(client_id, message)

    @Slot()
    def __on_socket_disconnected(self):
        """Handle socket disconnection.

        Args:
            conn (QTcpSocket): Socket object.

        Note:
            Emits disconnected signal.
        """
        try:
            self.socket.close()
        except RuntimeError:
            pass
        self.disconnected.emit(self.client_id)

    @Slot()
    def __on_socket_error(self):
        """Handle socket errors.

        Args:
            conn (QTcpSocket): Socket object.

        Note:
            Emits error signal.
        """
        error = self.socket.errorString()
        self.error.emit(self.client_id, Exception(error))


class NoBalancer(AbstractBalancer):


    def __init__(self):
        super(NoBalancer, self).__init__()
        self.workers = []

    @Slot(type, int)
    def balance(self, socket_type: type, socket_descriptor: int):
        client_id = self.get_next_socket_id()

        worker = _Worker(client_id, socket_type, socket_descriptor)
        worker.setObjectName(str(client_id))
        # worker.connected.connect(self.__on_worker_socket_connected)
        # worker.readyRead.connect(self.__on_worker_socket_readyRead)
        # worker.disconnected.connect()

        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        self.workers.append((worker, thread))

    # @Slot(str, int)
    # def __on_worker_socket_connected(self, ip: str, port: int):
    #     client_id = int(self.sender().objectName())
    #     self.connected.emit(client_id, ip, port)
    #
    # @Slot(bytes)
    # def __on_worker_socket_readyRead(self, data: bytes):
    #     client_id = int(self.sender().objectName())
    #     self.connected.emit(client_id, data)
    #
    # @Slot()
    # def __on_worker_socket_disconnected(self):
    #     client_id = int(self.sender().objectName())
    #     self.disconnected.emit(client_id)













