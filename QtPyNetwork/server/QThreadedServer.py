from qtpy.QtCore import Slot, Signal, QObject, QThread, Qt
from qtpy.QtNetwork import QTcpServer, QTcpSocket, QHostAddress

import json
import struct
import logging

from QtPyNetwork.models.Device import Device
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

    def __init__(self, socket_descriptor, client_id):
        super(SocketClient, self).__init__(None)
        self.socket_descriptor = socket_descriptor
        self.id = client_id

    @Slot()
    def get_id(self):
        return self.id

    @Slot()
    def run(self) -> None:
        """Run socket manager"""
        self._logger = logging.getLogger(self.__class__.__name__)  # noqa
        self.socket = QTcpSocket()  # noqa
        self.socket.setParent(None)
        if self.socket.setSocketDescriptor(self.socket_descriptor):  # noqa
            self.socket.readyRead.connect(self.on_message)  # noqa
            self.socket.disconnected.connect(self.on_disconnected)  # noqa
            self.socket.error.connect(self.on_error)  # noqa
            self._logger.debug("CLIENT-{} connected to "
                               "{}:{}".format(self.get_id(),
                                              self.socket.peerAddress().toString(),
                                              self.socket.peerPort()))

            self.connected.emit(int(self.get_id()), self.socket.peerAddress().toString(), self.socket.peerPort())
            self.close_signal.connect(self.close, Qt.BlockingQueuedConnection)
            self.write.connect(self._write)

    @Slot()
    def close(self):
        """Close connection.

        Note:
            Emits closed signal.
        """
        self.socket.close()
        self.socket.deleteLater()
        self.closed.emit()

    @Slot(dict)
    def _write(self, msg: dict):
        """Send task to client.

        Args:
            msg (dict): Message to send.
        """
        if self.socket:
            try:
                message = json.dumps(msg)
                message = message.encode()
                message = struct.pack('!L', len(message)) + message
                self.socket.write(message)
                self.socket.flush()
                self._logger.debug("CLIENT-{} Sent: {}".format(self.get_id(), message))
            except json.JSONDecodeError as e:
                self._logger.error("CLIENT-{} Could not encode message: {}".format(self.get_id(), e))
        else:
            self._logger.warning("Socket not created.")

    @Slot()
    def on_message(self):
        """Handle socket messages.

        Note:
            Emits message signal.
        """
        header_size = struct.calcsize('!L')
        header = self.socket.read(header_size)
        if len(header) == 4:
            msg_size = struct.unpack('!L', header)[0]
            message = self.socket.read(msg_size).decode()
        else:
            message = None
        if message:
            self._logger.debug("CLIENT-{} Received: {}".format(self.get_id(), message))
            try:
                message = json.loads(message)
                self.message.emit(int(self.get_id()), message)
            except json.JSONDecodeError as e:
                self._logger.error("CLIENT-{} Could not decode message: {}".format(self.get_id(), e))

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
        self.started.emit()

        self.write.connect(self._write)
        self.writeAll.connect(self._writeAll)

    @Slot(int)
    def on_incoming_connection(self, socket_descriptor: int) -> None:
        """Create new client thread.

        Args:
            socket_descriptor (int): Socket descriptor.
        """
        thread = QThread()
        client = SocketClient(socket_descriptor, self.get_free_id())
        client.moveToThread(thread)
        thread.started.connect(client.run)  # noqa

        client.connected.connect(self.connected.emit)  # noqa
        client.message.connect(self.message.emit)  # noqa
        client.error.connect(self.error.emit)
        client.disconnected.connect(self._on_client_disconnected)

        client.disconnected.connect(thread.quit)  # noqa
        client.disconnected.connect(thread.wait)  # noqa

        self.clients.append(client)
        self.threads.append(thread)
        thread.start()

        self._logger.info("Started new client thread!")
        self._logger.debug("Active clients: {}".format(sum([1 for x in self.threads if x.isRunning()])))

    @Slot(int)
    def _on_client_disconnected(self, client_id: int):
        self.clients.remove(self._get_client_by_id(client_id))
        self.disconnected.emit(client_id)

    @Slot(int)
    def _get_client_by_id(self, client_id: int):
        """Returns client object associated to provided ID.

        Args:
            client_id (int): Client ID.
        """
        for client in self.clients:
            if client.get_id() == client_id:
                return client
        return None

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
