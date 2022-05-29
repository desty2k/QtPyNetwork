from qtpy.QtCore import Slot, Signal, QObject, QThread
from qtpy.QtNetwork import QAbstractSocket

import logging

from QtPyNetwork.common import DataBuffer
from .AbstractBalancer import AbstractBalancer


class _Worker(QObject):
    disconnected = Signal(int)
    connected = Signal(int, str, int)
    ready_read = Signal(int, bytes)
    error = Signal(int, Exception)
    closed = Signal()

    close_signal = Signal()
    write_signal = Signal(bytes)

    def __init__(self, client_id, socket_type: type, socket_descriptor: int):
        super(_Worker, self).__init__()
        self.logger = logging.getLogger(f"ThreadBalancerWorker-{client_id}")
        self.socket: QAbstractSocket = None
        self.buffer = None
        self.client_id = client_id
        self.socket_type = socket_type
        self.socket_descriptor = socket_descriptor

        self.size_left = 0
        self.data = b""

        self.close_signal.connect(self.__on_close_signal)
        self.write_signal.connect(self.__on_write_signal)

    @Slot()
    def start(self):
        socket: QAbstractSocket = self.socket_type()
        socket.setParent(None)
        if socket.setSocketDescriptor(self.socket_descriptor):
            # socket.readyRead.connect(self.__on_socket_ready_read)
            socket.disconnected.connect(self.__on_socket_disconnected)
            socket.error.connect(self.__on_socket_error)
            socket.setObjectName(str(self.client_id))
            self.socket = socket
            self.buffer = DataBuffer(self.socket)
            self.buffer.data.connect(lambda data: self.ready_read.emit(self.client_id, data))

            self.logger.debug(f"New client - {socket.objectName()} - "
                              f"{socket.peerAddress().toString()} - {socket.peerPort()}")
            self.connected.emit(int(socket.objectName()), socket.peerAddress().toString(), socket.peerPort())

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

    @Slot()
    def __on_close_signal(self):
        """Close socket.

        Note:
            Emits closed signal.
        """
        try:
            self.socket.close()
        except RuntimeError:
            pass
        self.closed.emit()

    @Slot(bytes)
    def __on_write_signal(self, data: bytes):
        """Write data to socket.

        Args:
            data (bytes): Data to write.

        Note:
            Emits written signal.
        """
        self.buffer.write(data)
        # write(self.socket, data)

        # data = pack(HEADER, len(data)) + data
        # self.socket.write(data)
        # self.socket.flush()


class ThreadBalancer(AbstractBalancer):

    def __init__(self):
        super(ThreadBalancer, self).__init__()
        self.workers = []

    @Slot(type, int)
    def balance(self, socket_type: type, socket_descriptor: int) -> int:
        client_id = self.get_next_socket_id()

        worker = _Worker(client_id, socket_type, socket_descriptor)
        worker.setObjectName(str(client_id))
        # worker.connected.connect(self.__on_worker_socket_connected)
        # worker.ready_read.connect(self.__on_worker_socket_readyRead)
        # worker.disconnected.connect()
        worker.connected.connect(self.connected.emit)
        worker.disconnected.connect(self.disconnected.emit)
        worker.ready_read.connect(self.message.emit)
        worker.error.connect(self.client_error.emit)

        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.start)
        self.workers.append((worker, thread))
        thread.start()
        return client_id

    @Slot(int, bytes)
    def write(self, client_id: int, message: bytes):
        worker = self.__get_worker_by_client_id(client_id)
        if worker:
            worker.write_signal.emit(message)
        else:
            self.client_error.emit(client_id, Exception("Client not found"))

    @Slot(bytes)
    def write_all(self, message: bytes):
        for worker in self.workers:
            worker.write_signal.emit(message)

    @Slot(int)
    def disconnect(self, client_id: int):
        worker = self.__get_worker_by_client_id(client_id)
        if worker:
            worker.close_signal.emit()

    @Slot()
    def close(self):
        for worker in self.workers:
            worker.close_signal.emit()
        self.closed.emit()

    @Slot(int)
    def __get_worker_by_client_id(self, client_id: int):
        for worker, thread in self.workers:
            if worker.objectName() == str(client_id):
                return worker
