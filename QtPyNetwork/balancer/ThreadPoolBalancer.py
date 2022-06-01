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
    connection_signal = Signal(type, int, int)
    disconnect_signal = Signal(int)
    write_signal = Signal(int, bytes)

    def __init__(self):
        super(_Worker, self).__init__()
        self.logger = None

        self.sockets = {}
        self.close_signal.connect(self.__on_close_signal)
        self.write_signal.connect(self.__on_write_signal)
        self.connection_signal.connect(self.__on_connection_signal)
        self.disconnect_signal.connect(self.__on_disconnect_signal)

    @Slot()
    def start(self):
        self.logger = logging.getLogger(f"ThreadPoolBalancerWorker-{self.objectName()}")

    @Slot(type, int, int)
    def __on_connection_signal(self, socket_type: type, client_id: int, socket_descriptor: int):
        socket: QAbstractSocket = socket_type()
        socket.setParent(None)
        if socket.setSocketDescriptor(socket_descriptor):
            socket.disconnected.connect(self.__on_socket_disconnected)
            socket.error.connect(self.__on_socket_error)
            socket.setObjectName(str(client_id))

            buffer = DataBuffer(socket)
            buffer.data.connect(lambda data: self.ready_read.emit(client_id, data))

            self.sockets[client_id] = (socket, buffer)
            self.logger.debug(f"New client - {socket.objectName()} - "
                              f"{socket.peerAddress().toString()} - {socket.peerPort()}")
            self.connected.emit(int(socket.objectName()), socket.peerAddress().toString(), socket.peerPort())

    @Slot()
    def __on_socket_disconnected(self):
        """Handle socket disconnection.

        Note:
            Emits disconnected signal.
        """
        socket = self.sender()
        client_id = int(socket.objectName())
        try:
            if socket:
                socket.close()
        except RuntimeError:
            pass
        self.disconnected.emit(client_id)

    @Slot()
    def __on_socket_error(self):
        """Handle socket errors.

        Note:
            Emits error signal.
        """
        socket = self.sender()
        error = socket.errorString()
        self.error.emit(int(socket.objectName()), Exception(error))

    @Slot()
    def __on_close_signal(self):
        """Close socket.

        Note:
            Emits closed signal.
        """
        for client_id, socket_buffer in self.sockets.items():
            try:
                socket_buffer[0].close()
            except RuntimeError:
                pass
        self.closed.emit()

    @Slot(int, bytes)
    def __on_write_signal(self, client_id: int, data: bytes):
        """Write data to socket.

        Args:
            data (bytes): Data to write.

        Note:
            Emits written signal.
        """
        socket_buffer = self.sockets.get(client_id)
        if socket_buffer:
            socket_buffer[1].write(data)

    @Slot(int)
    def __on_disconnect_signal(self, client_id: int):
        for connected_client_id, socket_buffer in self.sockets.items():
            if connected_client_id == client_id:
                try:
                    socket_buffer[0].close()
                except RuntimeError:
                    pass


class ThreadPoolBalancer(AbstractBalancer):

    def __init__(self, threads=QThread.idealThreadCount()):
        super().__init__()
        self.__workers = []
        self.__start_worker(threads)

    @Slot(type, int)
    def balance(self, socket_type: type, socket_descriptor: int) -> int:
        client_id = self.get_next_socket_id()
        sockets_per_worker = [len(worker.sockets) for worker, thread in self.__workers]
        worker = self.__workers[sockets_per_worker.index(min(sockets_per_worker))][0]
        worker.connection_signal.emit(socket_type, client_id, socket_descriptor)
        return client_id

    @Slot(int)
    def __start_worker(self, thread_count: int):
        for i in range(thread_count):
            worker = _Worker()
            worker.setObjectName(str(i))
            worker.connected.connect(self.connected.emit)
            worker.disconnected.connect(self.disconnected.emit)
            worker.ready_read.connect(self.message.emit)
            worker.error.connect(self.client_error.emit)

            thread = QThread()
            worker.moveToThread(thread)
            thread.started.connect(worker.start)
            self.__workers.append((worker, thread))
            thread.start()

    @Slot(int, bytes)
    def write(self, client_id: int, message: bytes):
        worker = self.__get_worker_by_client_id(client_id)
        if worker:
            worker.write_signal.emit(client_id, message)
        else:
            self.client_error.emit(client_id, Exception("Client not found"))

    @Slot(bytes)
    def write_all(self, message: bytes):
        for worker in self.__workers:
            worker.write_signal.emit(message)

    @Slot(int)
    def disconnect(self, client_id: int):
        worker = self.__get_worker_by_client_id(client_id)
        if worker:
            worker.disconnect_signal.emit(client_id)

    @Slot()
    def close(self):
        for worker, thread in self.__workers:
            worker.close_signal.emit()

    @Slot(int)
    def wait(self, timeout: int = 0) -> None:
        timeout = timeout / len(self.__workers) if timeout > 0 else 0
        for worker, thread in self.__workers:
            thread.wait(timeout)

    @Slot()
    def is_running(self) -> bool:
        return any(thread.isRunning() for worker, thread in self.__workers)

    @Slot(int)
    def __get_worker_by_client_id(self, client_id: int):
        for worker, thread in self.__workers:
            if client_id in worker.sockets:
                return worker
