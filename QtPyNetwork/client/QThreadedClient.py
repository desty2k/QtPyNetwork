import json
import struct
import logging

from qtpy.QtNetwork import QTcpSocket, QHostAddress, QAbstractSocket
from qtpy.QtCore import QObject, QIODevice, Signal, QMetaObject, Slot, QThread, Qt

from QtPyNetwork.core.crypto import encrypt, decrypt


class SocketClient(QObject):
    closed = Signal()
    connected = Signal(str, int)
    message = Signal(dict)
    disconnected = Signal()
    error = Signal(str)
    failed_to_connect = Signal(str, int)

    close_signal = Signal()
    write_signal = Signal(dict)
    connect_signal = Signal(str, int, bytes)
    disconnect_signal = Signal()

    json_encoder = None
    json_decoder = None

    def __init__(self, ip: str, port: int, key: bytes, loggerName=None):
        super(SocketClient, self).__init__(None)
        self.ip = ip
        self.port = port
        self.key = key
        self.old_key = key
        self.logger_name = loggerName

    @Slot()
    def start(self):
        if self.logger_name:
            self.logger = logging.getLogger(self.logger_name)  # noqa
        else:
            self.logger = logging.getLogger(self.__class__.__name__)  # noqa
        self.data = {"size_left": 0, "data": b""}  # noqa
        self.tcpSocket = QTcpSocket(self)  # noqa

        self.tcpSocket.setObjectName("qclient_socket")
        QMetaObject.connectSlotsByName(self)
        self.tcpSocket.setSocketOption(QAbstractSocket.KeepAliveOption, 1)
        self.tcpSocket.connectToHost(QHostAddress(self.ip), self.port, QIODevice.ReadWrite)
        if not self.tcpSocket.waitForConnected(3000):
            self.failed_to_connect.emit(self.ip, self.port)
            self.tcpSocket.disconnectFromHost()
            self.tcpSocket.close()
            self.logger.error("Failed to connect to {}:{}".format(self.ip, self.port))
            return

        self.close_signal.connect(self.close, Qt.BlockingQueuedConnection)
        self.write_signal.connect(self._write)
        self.connect_signal.connect(self._connectTo)
        self.disconnect_signal.connect(self._disconnect)

    @Slot(dict)
    def _write(self, message: dict):
        """Write dict to server"""
        if self.json_encoder:
            message = json.dumps(message, cls=self.json_encoder)
        else:
            message = json.dumps(message)
        message = message.encode()
        if self.key:
            message = encrypt(message, self.key)
        message = struct.pack('!L', len(message)) + message
        self.tcpSocket.write(message)
        self.tcpSocket.flush()

    @Slot(int)
    def on_qclient_socket_error(self, error):
        self.logger.error(self.tcpSocket.errorString())
        self.error.emit(error)

    @Slot()
    def on_qclient_socket_connected(self):
        ip = self.tcpSocket.peerAddress().toString()
        port = int(self.tcpSocket.peerPort())
        self.logger.debug("Connected to {}:{}".format(ip, port))
        self.connected.emit(ip, port)

    @Slot()
    def on_qclient_socket_disconnected(self):
        self.logger.info("Disconnected from server")
        self.disconnected.emit()

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
            self.message.emit(message)
        except json.JSONDecodeError as e:
            self.error.emit("Failed to decode {}: {}".format(message, e))

    @Slot()
    def on_qclient_socket_readyRead(self):
        while self.tcpSocket.bytesAvailable():
            size_left = self.data.get("size_left")
            if size_left > 0:
                message = self.tcpSocket.read(size_left)
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
                header = self.tcpSocket.read(header_size)
                if len(header) == 4:
                    msg_size = struct.unpack('!L', header)[0]
                    message = self.tcpSocket.read(msg_size)

                    if len(message) < msg_size:
                        msg_size = msg_size - len(message)
                        self.data["data"] = message
                        self.data["size_left"] = msg_size
                    else:
                        self.__process_message(message)

    @Slot(bytes)
    def setCustomKey(self, key: bytes):
        """Sets custom encryption key."""
        self.key = key

    @Slot()
    def clearCustomKey(self):
        """Removes custom key."""
        self.key = self.old_key

    @Slot(str, int, bytes)
    def _connectTo(self, ip: str, port: int, key: bytes):
        self._disconnect()
        self.ip = ip
        self.port = port
        self.key = key
        self.run()

    @Slot()
    def _disconnect(self):
        self.tcpSocket.disconnectFromHost()

    @Slot()
    def close(self):
        self._disconnect()
        self.tcpSocket.close()
        self.closed.emit()


class QThreadedClient(QObject):
    """Threaded socket client.

    Available signals:
        - finished(): When client thread stops.
        - closed(): After closing socket.
        - connected(ip: str, port: int): Successfully connected to server.
        - message(data: dict): Received message from server.
        - disconnected(): Disconnected from server.
        - error(error_string: str): Socket error.
        - failed_to_connect(ip: str, port: int): Failed to connect to server.

    Available slots:
        - start(): Start client.
        - write(data: dict): Write message to server.
        - close(): Close connection.
        - disconnectFromServer(): Disconnect from server.
        - connectTo(ip: str, port: int, key: bytes): (Re)connect to server.
    """
    finished = Signal()
    closed = Signal()
    connected = Signal(str, int)
    message = Signal(dict)
    disconnected = Signal()
    error = Signal(str)
    failed_to_connect = Signal(str, int)

    def __init__(self, loggerName=None):
        super(QThreadedClient, self).__init__(None)
        self.__ip = None
        self.__port = None
        self.__key = None

        self.__client = None
        self.__client_thread = None
        self.__logger_name = loggerName

    @Slot()
    def start(self, ip: str, port: int, key: bytes):
        """Start client thread and connect to server."""
        self.__ip = ip
        self.__port = port
        self.__key = key

        self.__client = SocketClient(self.__ip, self.__port, self.__key, loggerName=self.__logger_name)
        self.__client_thread = QThread()

        self.__client_thread.started.connect(self.__client.start)
        self.__client_thread.finished.connect(self.finished.emit)

        self.__client.moveToThread(self.__client_thread)

        self.__client.connected.connect(self.connected.emit)
        self.__client.failed_to_connect.connect(self.failed_to_connect.emit)
        self.__client.message.connect(self.message.emit)
        self.__client.disconnected.connect(self.disconnected.emit)
        self.__client.error.connect(self.error.emit)
        self.__client.closed.connect(self.closed.emit)

        self.__client_thread.start()

    @Slot(dict)
    def write(self, data: dict):
        """write data to server.

        Args:
            data (dict): Data to write.
        """
        self.__client.write_signal.emit(data)

    @Slot(bytes)
    def setCustomKey(self, key: bytes):
        """Sets custom encryption key."""
        if self.__client and self.__client_thread:
            self.__client.setCustomKey(key)
        else:
            self.error.emit("Failed to set custom key - client not running")

    @Slot()
    def clearCustomKey(self):
        """Removes custom key."""
        if self.__client and self.__client_thread:
            self.__client.clearCustomKey()
        else:
            self.error.emit("Failed to clear custom key - client not running")

    @Slot(json.JSONEncoder)
    def setJSONEncoder(self, encoder):
        SocketClient.json_encoder = encoder

    @Slot(json.JSONDecoder)
    def setJSONDecoder(self, decoder):
        SocketClient.json_decoder = decoder

    @Slot()
    def close(self):
        """Disconnect from server and close socket."""
        if self.__client and self.__client_thread:
            self.__client.close_signal.emit()
            self.__client_thread.quit()
        else:
            self.error.emit("Client not running")

    @Slot()
    def disconnectFromServer(self):
        """Disconnect from server."""
        self.__client.disconnect_signal.emit()

    @Slot(str, int, bytes)
    def connectTo(self, ip: str, port: int, key: bytes):
        """(Re)connect to server.

        Args:
            ip (str): IP address.
            port (int): Port.
            key (bytes): Encryption key.
        """
        self.__client.connect_signal.emit(ip, port, key)

    @Slot()
    def isRunning(self):
        """Check if server is running"""
        return self.__client_thread.isRunning()

    @Slot()
    def wait(self):
        """Wait for server thread to finish."""
        return self.__client_thread.wait()
