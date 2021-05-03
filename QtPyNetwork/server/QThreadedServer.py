from qtpy.QtCore import Slot, Signal, QObject, QThread, Qt
from qtpy.QtNetwork import QTcpSocket, QAbstractSocket

import json
import struct
import logging

from QtPyNetwork.core.crypto import encrypt, decrypt
from QtPyNetwork.server.BaseServer import QBaseServer


class SocketClient(QObject):
    disconnected = Signal(int)
    connected = Signal(int, str, int)
    message = Signal(int, dict)
    error = Signal(int, str)
    closed = Signal()

    connection = Signal(int, int)
    close_signal = Signal()

    write = Signal(dict)

    json_encoder = None
    json_decoder = None

    def __init__(self, socket_descriptor, client_id, key):
        super(SocketClient, self).__init__(None)
        self.socket_descriptor = socket_descriptor
        self.id = client_id
        self.key = key
        self.old_key = key

    @Slot()
    def run(self) -> None:
        """Run socket manager"""
        self._logger = logging.getLogger(self.__class__.__name__)  # noqa
        self.data = {"size_left": 0, "data": b""}  # noqa
        self.socket = QTcpSocket()  # noqa
        self.socket.setParent(None)  # noqa
        self.socket.setSocketOption(QAbstractSocket.KeepAliveOption, 1)
        if self.socket.setSocketDescriptor(self.socket_descriptor):  # noqa
            self.socket.readyRead.connect(self.on_message)  # noqa
            self.socket.disconnected.connect(self.on_disconnected)  # noqa
            self.socket.error.connect(self.on_error)  # noqa
            self._logger.debug("CLIENT-{} connected to {}:{}".format(self.get_id(),
                                                                     self.socket.peerAddress().toString(),
                                                                     self.socket.peerPort()))

            self.connected.emit(int(self.get_id()), self.socket.peerAddress().toString(), self.socket.peerPort())
            self.close_signal.connect(self.close, Qt.BlockingQueuedConnection)
            self.write.connect(self._write)

    @Slot()
    def get_id(self):
        return self.id

    @Slot(bytes)
    def setCustomKey(self, key: bytes):
        """Sets custom encryption key."""
        self.key = key

    @Slot()
    def clearCustomKey(self):
        """Removes custom key."""
        self.key = self.old_key

    @Slot(dict)
    def _write(self, msg: dict):
        """Send task to client.

        Args:
            msg (dict): Message to send.
        """
        if self.socket:
            try:
                if self.json_encoder:
                    message = json.dumps(msg, cls=self.json_encoder)
                else:
                    message = json.dumps(msg)
                message = message.encode()
                if self.key:
                    message = encrypt(message, self.key)
                message = struct.pack('!L', len(message)) + message
                self.socket.write(message)
                self.socket.flush()
                # self._logger.debug("CLIENT-{} Sent: {}".format(self.get_id(), message))
            except json.JSONDecodeError as e:
                pass
                # self._logger.error("CLIENT-{} Could not encode message: {}".format(self.get_id(), e))
        else:
            self._logger.warning("Socket not created.")

    @Slot()
    def on_message(self):
        """Handle socket messages.

        Note:
            Emits message signal.
        """
        while self.socket.bytesAvailable():
            size_left = self.data.get("size_left")
            if size_left > 0:
                message = self.socket.read(size_left)
                size_left = size_left - len(message)
                if size_left > 0:
                    self.data["size_left"] = size_left
                    self.data["data"] += message
                else:
                    message = self.data.get("data") + message
                    self.data["size_left"] = 0
                    self.data["data"] = b""
                    self.__process_message(message)
            else:
                header_size = struct.calcsize('!L')
                header = self.socket.read(header_size)
                if len(header) == 4:
                    msg_size = struct.unpack('!L', header)[0]
                    message = self.socket.read(msg_size)

                    if len(message) < msg_size:
                        msg_size = msg_size - len(message)
                        self.data["data"] = message
                        self.data["size_left"] = msg_size
                    else:
                        self.__process_message(message)

    @Slot(bytes)
    def __process_message(self, message):
        if self.key:
            message = decrypt(message, self.key)
        message = message.decode()
        try:
            if self.json_decoder:
                message = json.loads(message, cls=self.json_decoder)
            else:
                message = json.loads(message)
            self.message.emit(int(self.get_id()), message)
        except json.JSONDecodeError as e:
            self.error.emit(int(self.get_id()), "Failed to decode {}: {}".format(message, e))

    @Slot()
    def on_disconnected(self):
        """Handle disconnecting socket.

        Note:
            Emits disconnected signal.
        """
        if self.socket:
            try:
                self._logger.info("CLIENT-{} Disconnected {}: {}:{}".format(self.get_id(), self.socket.peerName(),
                                                                            self.socket.peerAddress().toString(),
                                                                            self.socket.peerPort()))
                self.socket.close()
                self.disconnected.emit(int(self.get_id()))
            except RuntimeError:
                # when deleteLater is faster than "disconnected" signal
                pass

    @Slot()
    def on_error(self):
        """Handle socket errors

        Note:
            Emits error signal.
        """
        e = self.socket.errorString()
        self._logger.error("CLIENT-{} Error: {}".format(self.get_id(), e))
        self.error.emit(self.get_id(), str(e))

    @Slot()
    def close(self):
        """Close connection.

        Note:
            Emits closed signal.
        """
        self.socket.close()
        self.socket.deleteLater()
        self.closed.emit()


class ThreadedSocketHandler(QObject):
    """Creates client threads.

    Signals:
        - started (): Handler started.
        - finished (): Handler finished.
        - message (client_id: int, message: dict): Message received.
        - close_signal (): Emit this to close handler from another thread.
        - connection (client_id: int): New connection.
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

    def __init__(self, key=None):
        super(ThreadedSocketHandler, self).__init__(None)
        self.key = key

    @Slot()
    def start(self):
        """Start server."""
        self._logger = logging.getLogger(self.__class__.__name__)  # noqa
        self.clients = []  # noqa
        self.threads = []  # noqa

        self.close_signal.connect(self.close, Qt.BlockingQueuedConnection)
        self.write.connect(self._write)
        self.writeAll.connect(self._writeAll)
        self.kick.connect(self._kick)

        self.started.emit()

    @Slot(int)
    def on_incoming_connection(self, socket_descriptor: int) -> None:
        """Create new client thread.

        Args:
            socket_descriptor (int): Socket descriptor.
        """
        client_id = self.get_free_id()

        thread = QThread()
        thread.setObjectName(str(client_id))
        client = SocketClient(socket_descriptor, client_id, self.key)
        client.moveToThread(thread)
        thread.started.connect(client.run)  # noqa

        client.connected.connect(self.connected.emit)
        client.message.connect(self.message.emit)
        client.error.connect(self.error.emit)
        client.disconnected.connect(self.on_client_disconnected)

        client.disconnected.connect(thread.quit)
        client.disconnected.connect(thread.wait)
        thread.finished.connect(self.on_thread_finished)

        self.clients.append(client)
        self.threads.append(thread)
        thread.start()

        self._logger.info("Started new client thread!")
        self._logger.debug("Active clients: {}".format(len([x for x in self.threads if x.isRunning()])))

    @Slot(int)
    def on_client_disconnected(self, client_id: int):
        self.clients.remove(self.get_client_by_id(client_id))
        self.disconnected.emit(client_id)

    @Slot()
    def on_thread_finished(self):
        self.threads = [thread for thread in self.threads if thread.isRunning()]

    @Slot(int)
    def get_client_by_id(self, client_id: int):
        """Returns client object associated to provided ID.

        Args:
            client_id (int): Client ID.
        """
        for client in self.clients:
            if client.get_id() == client_id:
                return client
        return None

    @Slot()
    def get_free_id(self) -> int:
        """Returns not used device ID."""
        used = sorted(i.get_id() for i in self.clients)
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
        for client in self.clients:
            if client.get_id() == bot_id:
                client.setCustomKey(key)

    @Slot(int)
    def removeCustomKeyForClient(self, bot_id: int):
        """Removes custom key for client."""
        for client in self.clients:
            if client.get_id() == bot_id:
                client.clearCustomKey()

    @Slot()
    def clearCustomKeys(self):
        """Removes custom key for all clients."""
        for client in self.clients:
            client.clearCustomKey()

    @Slot(json.JSONEncoder)
    def setJSONEncoder(self, encoder):
        SocketClient.json_encoder = encoder

    @Slot(json.JSONDecoder)
    def setJSONDecoder(self, decoder):
        SocketClient.json_decoder = decoder

    @Slot(int, dict)
    def _write(self, client_id: int, msg: dict) -> None:
        """Write to client with ID.

        Args:
            client_id (int): Client ID.
            msg (dict): Message.
        """
        for client in self.clients:
            if client.get_id() == client_id:
                client.write.emit(msg)
                return
        self._logger.error("Could not find client with ID: {}!".format(client_id))

    @Slot(dict)
    def _writeAll(self, msg: dict) -> None:
        """Write to all clients.

        Args:
            msg (dict): Message.
        """
        for client in self.clients:
            client.write.emit(msg)

    @Slot(int)
    def _kick(self, device_id: int) -> None:
        """Kick client with ID.

        Args:
            device_id (int): Client ID.
        """
        for client in self.clients:
            if client.get_id() == device_id:
                client.close_signal.emit()
                return
        self.__logger.error("Could not find client with ID: {}!".format(device_id))

    @Slot()
    def close(self) -> None:
        """Close server and disconnect all clients.

        Note:
            Emits finished signal when successfully closed.
        """
        for client in self.clients:
            client.close_signal.emit()
            client.deleteLater()
        for thread in self.threads:
            thread.quit()

        self._logger.debug("Socket handler closed successfully")
        self.finished.emit()


class QThreadedServer(QBaseServer):
    """Socket server with dynamic amount of threads. When client connects,
    handler creates new thread and passes socket descriptor to that thread. """

    def __init__(self, *args, **kwargs):
        super(QThreadedServer, self).__init__(*args, **kwargs)
        self.setHandlerClass(ThreadedSocketHandler)
