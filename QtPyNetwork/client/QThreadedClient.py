import json
import struct
import logging

from qtpy.QtNetwork import QTcpSocket, QHostAddress, QAbstractSocket
from qtpy.QtCore import QObject, QIODevice, Signal, QMetaObject, Slot, QThread, Qt


class SocketClient(QObject):
    closed = Signal()
    connected = Signal(str, int)
    message = Signal(bytes)
    disconnected = Signal()
    error = Signal(str)
    failed_to_connect = Signal(str, int)

    close_signal = Signal()
    write_signal = Signal(bytes)
    reconnect_signal = Signal()
    connect_signal = Signal(str, int)
    disconnect_signal = Signal()

    def __init__(self, ip: str, port: int, loggerName=None):
        super(SocketClient, self).__init__(None)
        self.ip = ip
        self.port = port
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
        self.reconnect_signal.connect(self._reconnect)

    @Slot(bytes)
    def _write(self, message: bytes):
        """Write dict to server"""
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
                    self.message.emit(message)
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
                        self.message.emit(message)

    @Slot(str, int)
    def _connectTo(self, ip: str, port: int):
        self._disconnect()
        self.ip = ip
        self.port = port
        self.start()

    @Slot()
    def _reconnect(self):
        self._disconnect()
        self.start()

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
        - write(data: bytes): Write message to server.
        - reconnect(): Reconnect to server.
        - close(): Close connection.
        - disconnect_from_server(): Disconnect from server.
        - connect_to(ip: str, port: int): (Re)connect to server.
    """
    finished = Signal()
    closed = Signal()
    connected = Signal(str, int)
    message = Signal(bytes)
    disconnected = Signal()
    error = Signal(str)
    failed_to_connect = Signal(str, int)

    def __init__(self, loggerName=None):
        super(QThreadedClient, self).__init__(None)
        self.__ip = None
        self.__port = None

        self.__client = None
        self.__client_thread = None
        self.__logger_name = loggerName

    @Slot(str, int)
    def start(self, ip: str, port: int):
        """Start client thread and connect to server."""
        self.__ip = ip
        self.__port = port

        self.__client = SocketClient(self.__ip, self.__port, loggerName=self.__logger_name)
        self.__client_thread = QThread()

        self.__client_thread.started.connect(self.__client.start)
        self.__client_thread.finished.connect(self.finished.emit)

        self.__client.moveToThread(self.__client_thread)

        self.__client.connected.connect(self.on_connected)
        self.__client.failed_to_connect.connect(self.on_failed_to_connect)
        self.__client.message.connect(self.on_message)
        self.__client.disconnected.connect(self.on_disconnected)
        self.__client.error.connect(self.on_error)
        self.__client.closed.connect(self.on_closed)

        self.__client_thread.start()

    @Slot(str, int)
    def on_connected(self, ip, port):
        self.connected.emit(ip, port)

    @Slot(str, int)
    def on_failed_to_connect(self, ip, port):
        self.failed_to_connect.emit(ip, port)

    @Slot(bytes)
    def on_message(self, message: bytes):
        self.message.emit(message)

    @Slot()
    def on_disconnected(self):
        self.disconnected.emit()

    @Slot(str)
    def on_error(self, error: str):
        self.error.emit(error)

    @Slot()
    def on_closed(self):
        self.closed.emit()

    @Slot(bytes)
    def write(self, data: bytes):
        """Write data to server.

        Args:
            data (bytes): Data to write.
        """
        self.__client.write_signal.emit(data)

    @Slot()
    def close(self):
        """Disconnect from server and close socket."""
        if self.__client and self.__client_thread:
            self.__client.close_signal.emit()
            self.__client_thread.quit()
        else:
            self.error.emit("Client not running")

    @Slot()
    def disconnect_from_server(self):
        """Disconnect from server."""
        self.__client.disconnect_signal.emit()

    @Slot(str, int)
    def connect_to(self, ip: str, port: int):
        """(Re)connect to server.

        Args:
            ip (str): IP address.
            port (int): Port.
        """
        self.__client.connect_signal.emit(ip, port)

    @Slot()
    def reconnect(self):
        self.__client.reconnect_signal.emit()

    @Slot()
    def is_running(self):
        """Check if server is running"""
        if self.__client_thread:
            return self.__client_thread.isRunning()
        return False

    @Slot()
    def wait(self):
        """Wait for server thread to finish."""
        if self.__client_thread:
            return self.__client_thread.wait()
        return True
