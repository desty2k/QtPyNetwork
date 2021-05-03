from qtpy.QtCore import Slot, Signal, QObject, QThread, Qt
from qtpy.QtNetwork import QTcpSocket

import json
import struct
import logging

from QtPyNetwork.core.crypto import encrypt, decrypt
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
    kick = Signal(int)

    json_encoder = None
    json_decoder = None

    def __init__(self, key=b"", parent=None):
        super(SocketWorker, self).__init__(parent)
        self.key = key

    @Slot()
    def start(self) -> None:
        """Run socket worker."""
        self.keys = {}  # noqa
        self.sockets = []  # noqa
        self.data = {}  # noqa
        self.__logger = logging.getLogger(self.__class__.__name__)  # noqa

        self.connection.connect(self.on_connection, Qt.BlockingQueuedConnection)  # noqa
        self.close_signal.connect(self.close, Qt.BlockingQueuedConnection)

        self.write.connect(self._write)
        self.writeAll.connect(self._writeAll)
        self.kick.connect(self._kick)

    @Slot(int)
    def _kick(self, device_id):
        self.get_socket_by_id(device_id).close()

    @Slot(int, dict)
    def _write(self, device_id: int, msg: dict):
        """Send task to client. DO NOT USE THIS! Emit write signal instead!

        Args:
            device_id (int): Client ID.
            msg (dict): Message to send.
        """
        socket = self.get_socket_by_id(int(device_id))
        if socket:
            device_id = int(socket.objectName())
            try:
                if self.json_encoder:
                    message = json.dumps(msg, cls=self.json_encoder)
                else:
                    message = json.dumps(msg)

                message = message.encode()
                if device_id in self.keys:
                    message = encrypt(message, self.keys.get(device_id))
                elif self.key:
                    message = encrypt(message, self.key)

                message = struct.pack('!L', len(message)) + message
                socket.write(message)
                socket.flush()
            except json.JSONDecodeError as e:
                self.__logger.error("CLIENT-{} Could not encode message: {}".format(device_id, e))
        else:
            self.__logger.warning("Could not find socket with specified ID.")

    @Slot(dict)
    def _writeAll(self, msg: dict):
        """Send task to all connected clients. DO NOT USE THIS! Emit writeAll signal instead!

        Args:
            msg (dict): Message to send.
        """
        for socket in self.sockets:
            device_id = int(socket.objectName())
            try:
                if self.json_encoder:
                    message = json.dumps(msg, cls=self.json_encoder)
                else:
                    message = json.dumps(msg)
                message = message.encode()

                if device_id in self.keys:
                    message = encrypt(message, self.keys.get(device_id))
                elif self.key:
                    message = encrypt(message, self.key)

                message = struct.pack('!L', len(message)) + message
                socket.write(message)
                socket.flush()
            except json.JSONDecodeError as e:
                pass

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

    @Slot(int, bytes)
    def setCustomKeyForClient(self, bot_id: int, key: bytes):
        """Sets custom encryption key for one client."""
        self.keys[bot_id] = key

    @Slot(int)
    def removeCustomKeyForClient(self, bot_id: int):
        """Removes custom key for client."""
        del self.keys[bot_id]

    @Slot()
    def clearCustomKeys(self):
        """Removes custom key for all clients."""
        self.keys = {}  # noqa

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
        device_id = int(conn.objectName())
        while conn.bytesAvailable():
            if device_id in self.data:
                size_left = self.data.get(device_id).get("size_left")
                message = conn.read(size_left)
                size_left = size_left - len(message)
                if size_left > 0:
                    self.data[device_id]["size_left"] = size_left
                    self.data[device_id]["data"] += message
                else:
                    message = self.data.get(device_id).get("data") + message
                    del self.data[device_id]
                    self.__process_message(device_id, message)

            else:
                header_size = struct.calcsize('!L')
                header = conn.read(header_size)
                if len(header) == 4:
                    msg_size = struct.unpack('!L', header)[0]
                    message = conn.read(msg_size)

                    if len(message) < msg_size:
                        msg_size = msg_size - len(message)
                        self.data[device_id] = {"data": message, "size_left": msg_size}
                    else:
                        self.__process_message(device_id, message)

    @Slot(bytes)
    def __process_message(self, device_id, message):
        if device_id in self.keys:
            message = decrypt(message, self.keys.get(device_id))
        elif self.key:
            message = decrypt(message, self.key)

        message = message.decode()
        try:
            if self.json_decoder:
                message = json.loads(message, cls=self.json_decoder)
            else:
                message = json.loads(message)
            self.message.emit(device_id, message)
        except json.JSONDecodeError as e:
            self.error.emit("Failed to decode message from {}: {}: {}".format(device_id, message, e))

    @Slot(QTcpSocket)
    def on_disconnected(self, conn):
        """Handle socket disconnection.

        Args:
            conn (QTcpSocket): Socket object.

        Note:
            Emits disconnected signal.
        """
        device_id = int(conn.objectName())
        if conn in self.sockets:
            try:
                conn.close()
                self.sockets.remove(conn)
            except RuntimeError:
                pass
        if device_id in self.keys:
            del self.keys[device_id]
        if device_id in self.data:
            del self.data[device_id]
        self.__logger.info("CLIENT-{} Disconnected {}: {}:{}".format(device_id, conn.peerName(),
                                                                     conn.peerAddress().toString(),
                                                                     conn.peerPort()))
        self.disconnected.emit(device_id)

    @Slot(QTcpSocket)
    def on_error(self, conn: QTcpSocket):
        """Handle socket errors.

        Args:
            conn (QTcpSocket): Socket object.

        Note:
            Emits error signal.
        """
        device_id = int(conn.objectName())
        e = conn.errorString()
        self.__logger.error("CLIENT-{} Error: {}".format(device_id, e))
        self.error.emit(device_id, str(e))

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
    kick = Signal(int)

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
        self.kick.connect(self._kick)
        self.__logger.debug("Allocating {} worker threads...".format(self.cores))

        try:
            for i in range(self.cores):
                self.create_worker()

            self.__logger.info("Started worker threads!")
            self.__logger.debug("Active socket workers: {}".format(sum([1 for x in self.threads if x.isRunning()])))
            self.started.emit()

        except Exception as e:
            self.__logger.error("Failed to start socket handler: {}".format(e))
            self.close()

    @Slot()
    def create_worker(self):
        thread = QThread()
        worker = SocketWorker(self.key)
        worker.moveToThread(thread)

        worker.connected.connect(self.connected.emit)  # noqa
        worker.message.connect(self.message.emit)  # noqa
        worker.disconnected.connect(self.disconnected.emit)  # noqa
        worker.error.connect(self.error.emit)  # noqa

        thread.started.connect(worker.start)  # noqa
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
                worker.write.emit(device_id, msg)
                return
        self.__logger.error("Could not find client with ID: {}!".format(device_id))

    @Slot(int)
    def _kick(self, device_id: int) -> None:
        """Kick client with ID.

        Args:
            device_id (int): Client ID.
        """
        for worker in self.workers:
            if worker.has_device_id(device_id):
                worker.kick.emit(device_id)
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

    @Slot(int, bytes)
    def setCustomKeyForClient(self, bot_id: int, key: bytes):
        """Sets custom encryption key for one client."""
        for worker in self.workers:
            if worker.has_device_id(bot_id):
                worker.setCustomKeyForClient(bot_id, key)

    @Slot(int)
    def removeCustomKeyForClient(self, bot_id: int):
        """Removes custom key for client."""
        for worker in self.workers:
            if worker.has_device_id(bot_id):
                worker.removeCustomKeyForClient(bot_id)

    @Slot()
    def clearCustomKeys(self):
        """Removes custom key for all clients."""
        for worker in self.workers:
            worker.clearCustomKeys()

    @Slot(json.JSONEncoder)
    def setJSONEncoder(self, encoder):
        SocketWorker.json_encoder = encoder

    @Slot(json.JSONDecoder)
    def setJSONDecoder(self, decoder):
        SocketWorker.json_decoder = decoder

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
