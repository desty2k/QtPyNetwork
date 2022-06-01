from qtpy.QtCore import Slot, Signal
from qtpy.QtNetwork import QAbstractSocket

from struct import unpack, pack

from .AbstractBalancer import AbstractBalancer, HEADER, HEADER_SIZE


class NoBalancer(AbstractBalancer):
    def __init__(self):
        super(NoBalancer, self).__init__()
        self.data = {0: {
            "size_left": 0,
            "data": b"",
        }}
        self.sockets = []

    @Slot(type, int)
    def balance(self, socket_type: type, socket_descriptor: int):
        socket: QAbstractSocket = socket_type()
        socket.setParent(None)
        if socket.setSocketDescriptor(socket_descriptor):
            socket.readyRead.connect(self.__on_socket_ready_read)
            socket.disconnected.connect(self.__on_socket_disconnected)
            socket.error.connect(self.__on_socket_error)
            socket.setObjectName(str(self.get_next_socket_id()))
            self.sockets.append(socket)
            self.logger.debug(f"New client - {socket.objectName()} - "
                              f"{socket.peerAddress().toString()} - {socket.peerPort()}")
            self.connected.emit(int(socket.objectName()), socket.peerAddress().toString(), socket.peerPort())

    @Slot()
    def __on_socket_ready_read(self):
        """Handle socket messages.

        Note:
            Emits message signal.
        """
        socket = self.sender()
        client_id = int(socket.objectName())

        while socket.bytesAvailable():
            if client_id in self.data:
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

        Note:
            Emits disconnected signal.
        """
        socket = self.sender()
        client_id = int(socket.objectName())
        if socket in self.sockets:
            try:
                socket.close()
                self.sockets.remove(socket)
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
        client_id = int(socket.objectName())
        error = socket.errorString()
        self.client_error.emit(client_id, Exception(error))

    @Slot(int, bytes)
    def write(self, client_id: int, data: bytes):
        """Write data to socket.

        Args:
            client_id (int): Client ID.
            data (bytes): Data to write.
        """
        for socket in self.sockets:
            if int(socket.objectName()) == client_id:
                data = pack(HEADER, len(data)) + data
                socket.write(data)
                socket.flush()
                return
        self.client_error.emit(client_id, Exception(f"Client {client_id} not found"))

    @Slot(bytes)
    def write_all(self, message: bytes):
        """Write data to all sockets.

        Args:
            message (bytes): Data to write.
        """
        for socket in self.sockets:
            socket.write(message)
            socket.flush()

    @Slot(int)
    def disconnect(self, client_id: int):
        """Disconnect socket.

        Args:
            client_id (int): Client ID.
        """
        for socket in self.sockets:
            if int(socket.objectName()) == client_id:
                socket.disconnectFromHost()
                return
        self.client_error.emit(client_id, Exception(f"Client {client_id} not found"))

    @Slot()
    def close(self):
        """Close all sockets."""
        for socket in self.sockets:
            try:
                socket.disconnectFromHost()
                socket.close()
            except RuntimeError:
                pass
        self.sockets.clear()
