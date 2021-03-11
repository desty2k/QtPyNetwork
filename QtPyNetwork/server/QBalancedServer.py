from qtpy.QtCore import Slot, Signal, QObject, QThread, Qt
from qtpy.QtNetwork import QTcpServer, QTcpSocket, QHostAddress

import json
import struct
import logging

from QtPyNetwork.server.BaseServer import QBaseServer


class SocketWorker(QObject):
    """SocketWorker manages sockets and handles messages.

    Signals:
        - disconnected (device_id: int): Client disconnected.
        - connected (device_id: int, ip: str, port: int): Client connected
        - message (device_id: int, message: dict): Message from client.
        - error (device_id: int, error: str): Error occured.
        - closed (): Closed successfully.
        - send (device_id: int, message: dict): Emit to send message
        to client with ID in this thread.
        - send (message: dict): Emit to send message
        to all clients in this thread.
    """

    disconnected = Signal(int)
    connected = Signal(int, str, int)
    message = Signal(int, dict)
    error = Signal(int, str)
    closed = Signal()

    connection = Signal(int, int)
    close_signal = Signal()

    write = Signal(int, dict)
    writeAll = Signal(dict)

    def __init__(self, parent=None):
        super(SocketWorker, self).__init__(parent)

    @Slot()
    def start(self) -> None:
        """Run socket worker."""
        self.sockets = []  # noqa
        self.__logger = logging.getLogger(self.__class__.__name__)  # noqa

        self.connection.connect(self.on_connection, Qt.BlockingQueuedConnection)  # noqa
        self.close_signal.connect(self.close, Qt.BlockingQueuedConnection)

        self.write.connect(self._write)
        self.writeAll.connect(self._writeAll)

    @Slot()
    def close(self):
        """Close all connections.

        Note:
            Emits closed signal.
        """
        for conn in self.sockets:
            conn.close()
            try:
                conn.deleteLater()
                self.sockets.remove(conn)
            except ValueError:
                pass
        self.closed.emit()

    @Slot(int, dict)
    def _write(self, device_id: int, msg: dict):
        """Send task to client. DO NOT USE THIS! Emit write signal instead!

        Args:
            device_id (int): Client ID.
            msg (dict): Message to send.
        """
        socket = self.get_socket_by_id(int(device_id))
        if socket:
            try:
                message = json.dumps(msg)
                message = message.encode()
                message = struct.pack('!L', len(message)) + message
                socket.write(message)
                socket.flush()
                self.__logger.debug("CLIENT-{} Sent: {}".format(socket.objectName(), message))
            except json.JSONDecodeError as e:
                self.__logger.error("CLIENT-{} Could not encode message: {}".format(socket.objectName(), e))
        else:
            self.__logger.warning("Could not find socket with specified ID.")

    @Slot(dict)
    def _writeAll(self, msg: dict):
        """Send task to all connected clients. DO NOT USE THIS! Emit writeAll signal instead!

        Args:
            msg (dict): Message to send.
        """
        for socket in self.sockets:
            try:
                message = json.dumps(msg)
                message = message.encode()
                message = struct.pack('!L', len(message)) + message
                socket.write(message)
                socket.flush()
                self.__logger.debug("CLIENT-{} Sent: {}".format(socket.objectName(), message))
            except json.JSONDecodeError as e:
                self.__logger.error("CLIENT-{} Could not encode message: {}".format(socket.objectName(), e))

    @Slot(int)
    def get_socket_by_id(self, device_id: int):
        """Returns socket object associated to provided ID.

        Args:
            device_id (int): Socket ID.
        """
        for conn in self.sockets:
            if int(conn.objectName()) == int(device_id):
                return conn
        return None

    @Slot()
    def socket_count(self):
        """Returns amount of sockets."""
        return len(self.sockets)

    @Slot()
    def used_ids(self):
        """Returns used IDs."""
        return [int(x.objectName()) for x in self.sockets]

    @Slot(int)
    def has_device_id(self, device_id: int):
        """Check if this thread has socket with ID.

        Args:
            device_id (int): Socket ID.
        """
        return int(device_id) in [int(socket.objectName()) for socket in self.sockets]

    @Slot(int, int)
    def on_connection(self, device_id: int, socket_descriptor: int):
        """Create new QTcpSocket object and setup connection with client.

        Args:
            device_id (int): Socket ID.
            socket_descriptor (int) Socket descriptor.
        Note:
            Emits connected signal.
        """
        socket = QTcpSocket()
        socket.setParent(None)  # noqa
        if socket.setSocketDescriptor(socket_descriptor):  # noqa
            socket.readyRead.connect(lambda: self.on_message(socket))  # noqa
            socket.disconnected.connect(lambda: self.on_disconnected(socket))  # noqa
            socket.error.connect(lambda: self.on_error(socket))  # noqa
            socket.setObjectName(str(device_id))
            self.sockets.append(socket)
            self.__logger.debug("New connection from CLIENT-{} "
                                "IP: {}:{}".format(socket.objectName(),
                                                   socket.peerAddress().toString(),
                                                   socket.peerPort()))
            self.connected.emit(int(socket.objectName()), socket.peerAddress().toString(), socket.peerPort())

    @Slot(QTcpSocket)
    def on_message(self, conn):
        """Handle socket messages.

        Note:
            Emits message signal.
        """
        device_id = conn.objectName()

        header_size = struct.calcsize('!L')
        header = conn.read(header_size)
        if len(header) == 4:
            msg_size = struct.unpack('!L', header)[0]
            message = conn.read(msg_size).decode()
        else:
            message = None
        if message:
            self.__logger.debug("CLIENT-{} Received: {}".format(device_id, message))
            try:
                message = json.loads(message)
                self.message.emit(int(device_id), message)
            except json.JSONDecodeError as e:
                self.__logger.error("CLIENT-{} Could not decode message: {}".format(device_id, e))

    @Slot(QTcpSocket)
    def on_disconnected(self, conn):
        """Handle socket disconnection.

        Args:
            conn (QTcpSocket): Socket object.

        Note:
            Emits disconnected signal.
        """
        if conn in self.sockets:
            try:
                device_id = conn.objectName()
                self.__logger.info("CLIENT-{} Disconnected {}: {}:{}".format(device_id, conn.peerName(),
                                                                             conn.peerAddress().toString(),
                                                                             conn.peerPort()))
                conn.close()
                self.sockets.remove(conn)
                self.disconnected.emit(int(device_id))
            except RuntimeError:
                pass

    @Slot(QTcpSocket)
    def on_error(self, conn: QTcpSocket):
        """Handle socket errors.

        Args:
            conn (QTcpSocket): Socket object.

        Note:
            Emits error signal.
        """
        device_id = conn.objectName()
        e = conn.errorString()
        self.__logger.error("CLIENT-{} Error: {}".format(device_id, e))
        self.error.emit(device_id, str(e))


class BalancedSocketHandler(QObject):
    """Creates socket handlers threads. New connections
    are passed to SocketWorker with least load.

    Signals:
        - started (): Handler started.
        - finished (): Handler finished.
        - message (device_id: int, message: dict): Message received.
        - close_signal (): Emit this to close handler from another thread.
        - connection (device_id: int): New connection.
    """
    started = Signal()
    finished = Signal()
    close_signal = Signal()

    connected = Signal(int, str, int)
    message = Signal(int, dict)
    error = Signal(int, str)
    disconnected = Signal(int)

    write = Signal(int, dict)
    writeAll = Signal(dict)

    def __init__(self, cores=None, key=None):
        super(BalancedSocketHandler, self).__init__(None)
        self.cores = cores
        self.key = key

    @Slot()
    def start(self):
        """Start server and create socket handlers."""
        self.__logger = logging.getLogger(self.__class__.__name__)  # noqa
        self.workers = []  # noqa
        self.threads = []  # noqa
        if not self.cores:
            self.cores = QThread.idealThreadCount()

        self.close_signal.connect(self.close, Qt.BlockingQueuedConnection)
        self.write.connect(self._write)
        self.writeAll.connect(self._writeAll)
        self.__logger.debug("Allocating {} worker threads...".format(self.cores))

        try:
            for i in range(self.cores):
                thread = QThread()
                worker = SocketWorker()
                worker.moveToThread(thread)
                thread.started.connect(worker.start)  # noqa

                worker.connected.connect(self.connected.emit)  # noqa
                worker.message.connect(self.message.emit)  # noqa
                worker.disconnected.connect(self.disconnected.emit)
                worker.error.connect(self.error.emit)

                worker.closed.connect(thread.quit)  # noqa
                worker.closed.connect(thread.wait)  # noqa
                self.workers.append(worker)
                self.threads.append(thread)
                thread.start()
            self.__logger.info("Started worker threads!")
            self.__logger.debug("Active socket workers: {}".format(sum([1 for x in self.threads if x.isRunning()])))
            self.started.emit()

        except Exception as e:
            self.__logger.error("Failed to start socket handler: {}".format(e))
            self.close()

    @Slot()
    def create_worker(self):
        thread = QThread()
        worker = SocketWorker()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)  # noqa
        worker.closed.connect(thread.quit)  # noqa
        worker.closed.connect(thread.wait)  # noqa

        self.workers.append(worker)
        self.threads.append(thread)
        thread.start()

    @Slot(int)
    def on_incoming_connection(self, socket_descriptor: int) -> None:
        """Select thread with least sockets and setup connection.
        Assign not used ID.

        Args:
            socket_descriptor (int): Socket descriptor.
        """
        count_list = [x.socket_count() for x in self.workers]
        worker_id = count_list.index(min(count_list))
        device_id = self.get_free_id()
        self.workers[worker_id].connection.emit(device_id, socket_descriptor)

    @Slot(int, dict)
    def _write(self, device_id: int, msg: dict) -> None:
        """Write to client with ID.

        Args:
            device_id (int): Client ID.
            msg (dict): Message.
        """
        for worker in self.workers:
            if worker.has_device_id(device_id):
                worker.send.emit(device_id, msg)
                return
        self.__logger.error("Could not find client with ID: {}!".format(device_id))

    @Slot(dict)
    def _writeAll(self, msg: dict) -> None:
        """Write to all clients

        Args:
            msg (dict): Message.
        """
        for worker in self.workers:
            worker.writeAll.emit(msg)

    @Slot()
    def get_free_id(self) -> int:
        """Returns not used device ID."""
        used = []
        for i in self.workers:
            used = used + i.used_ids()
        used = sorted(used)
        if len(used) > 0:
            maxid = max(used)
            for i in range(1, maxid):
                if i not in used:
                    return i
            return maxid + 1
        else:
            return 1

    @Slot()
    def close(self) -> None:
        """Close server and all socket handlers.

        Note:
            Emits finished signal when successfully closed.
        """
        for worker in self.workers:
            worker.close_signal.emit()
            worker.deleteLater()
        for thread in self.threads:
            thread.quit()
        self.__logger.debug("Socket handler closed successfully")
        self.finished.emit()


class QBalancedServer(QBaseServer):
    def __init__(self, *args, **kwargs):
        super(QBalancedServer, self).__init__(*args, **kwargs)
        self.setHandlerClass(BalancedSocketHandler)
