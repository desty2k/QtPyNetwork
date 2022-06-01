from qtpy.QtCore import Slot, Signal, QObject, QThread
from qtpy.QtNetwork import QTcpServer, QHostAddress

from QtPyNetwork.model import Client
from QtPyNetwork.exception import NotConnectedError, ServerNotRunning

import logging

from QtPyNetwork.balancer import AbstractBalancer


class AbstractServer(QObject):
    started = Signal(str, int)
    closed = Signal()

    connected = Signal(Client, str, int)
    disconnected = Signal(Client)
    message = Signal(Client, bytes)

    client_error = Signal(Client, Exception)
    server_error = Signal(Exception)

    def __init__(self, balancer: AbstractBalancer):
        super(AbstractServer, self).__init__()
        self.clients: list[Client] = []
        self.server: QObject = None
        self.__client_model = Client

        self.balancer = balancer
        self.balancer.connected.connect(self.__on_balancer_client_connected)
        self.balancer.disconnected.connect(self.__on_balancer_client_disconnected)
        self.balancer.message.connect(self.__on_balancer_client_message)
        self.balancer.client_error.connect(self.__on_balancer_client_error)
        self.balancer.closed.connect(self.on_closed)

    @Slot(int, str, int)
    def __on_balancer_client_connected(self, client_id: int, ip: str, port: int):
        client = self.__client_model(self, client_id, ip, port)
        self.clients.append(client)
        self.on_connected(client, ip, port)

    @Slot(int, bytes)
    def __on_balancer_client_message(self, client_id: int, message: bytes):
        """When server receives message from client."""
        self.on_message(self.get_client_by_id(client_id), message)

    @Slot(int)
    def __on_balancer_client_disconnected(self, client_id: int):
        """When client disconnects from server."""
        client = self.get_client_by_id(client_id)
        if client:
            client.set_connected(False)
            self.clients.remove(client)
            self.on_disconnected(client)

    @Slot(int, Exception)
    def __on_balancer_client_error(self, client_id: int, error: Exception):
        self.on_client_error(self.get_client_by_id(client_id), error)

    @Slot(str, int)
    def start(self, ip: str, port: int):
        pass

    @Slot(str, int)
    def on_started(self, ip: str, port: int):
        self.started.emit(ip, port)

    @Slot(Client, str, int)
    def on_connected(self, client: Client, ip: str, port: int):
        """Called when new client connects to server.
        Emits connected signal.

        Args:
            client (Client): Client object.
            ip (str): Client ip address.
            port (int): Client port.
        """
        self.connected.emit(client, ip, port)

    @Slot(Client, bytes)
    def on_message(self, client: Client, message: bytes):
        """Called when server receives message from client.
        Emits message signal.

        Args:
            client (Client): Message sender.
            message (bytes): Message.
        """
        self.message.emit(client, message)

    @Slot(Client)
    def on_disconnected(self, client: Client):
        """Called when client disconnects from server.
        Emits disconnected signal.

        Args:
            client (Client): Disconnected client.
        """
        self.disconnected.emit(client)

    @Slot(Client, Exception)
    def on_client_error(self, client: Client, error: Exception):
        """Called when server error occurs.
        Emits error signal.

        Args:
            client (Client): Client object.
            error (Exception): Exception object.
        """
        self.client_error.emit(client, error)

    @Slot(Exception)
    def on_server_error(self, error: Exception):
        """Called when a client socket error occurs.
        Emits error signal.

        Args:
            error (Exception): Excpetion object.
        """
        self.server_error.emit(error)

    @Slot()
    def on_closed(self):
        self.closed.emit()

    @Slot(Client)
    def disconnect(self, client: Client):
        """Disconnects client from server.

        Args:
            client (Client): Client object.
        """
        self.balancer.disconnect(client.id())

    @Slot(Client, bytes)
    def write(self, client: Client, message: bytes):
        """Sends message to client.

        Args:
            client (Client): Client object.
            message (bytes): Message.
        """
        self.balancer.write(client.id(), message)

    @Slot(bytes)
    def write_all(self, message: bytes):
        """Sends message to all clients.

        Args:
            message (bytes): Message.
        """
        self.balancer.write_all(message)

    @Slot(int)
    def get_client_by_id(self, client_id: int):
        for client in self.clients:
            if client.id() == client_id:
                return client

    @Slot(Client)
    def set_client_model(self, model: Client):
        if not issubclass(model, Client):
            raise TypeError('model must be subclass of Client')
        self.__client_model = model

    @Slot()
    def is_running(self) -> bool:
        """Check if server is running."""
        pass

    @Slot()
    def wait(self) -> bool:
        """Wait for server thread to close."""
        pass

    @Slot()
    def close(self):
        pass
