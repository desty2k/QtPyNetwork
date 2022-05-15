from qtpy.QtCore import Slot, Signal
from qtpy.QtNetwork import QAbstractSocket, QUdpSocket

from struct import unpack

from .AbstractBalancer import AbstractBalancer


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

        Args:
            conn (QTcpSocket): Socket object.

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

        Args:
            conn (QTcpSocket): Socket object.

        Note:
            Emits error signal.
        """
        socket = self.sender()
        client_id = int(socket.objectName())
        error = socket.errorString()
        self.error.emit(client_id, Exception(error))

