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





















# class TCPServer(QTcpServer):
#     """Listens for incoming connections."""
#     connection = Signal(int)
#
#     def __init__(self, parent=None):
#         super(TCPServer, self).__init__(parent)
#
#     @Slot(int)
#     def incomingConnection(self, socket_descriptor):
#         self.connection.emit(int(socket_descriptor))
#
#
# class QAbstractServer(QObject):
#     """Server base for QtPyNetwork."""
#     connected = Signal(Device, str, int)
#     disconnected = Signal(Device)
#     message = Signal(Device, bytes)
#     error = Signal(Device, str)
#
#     server_error = Signal(str)
#     closed = Signal()
#
#     def __init__(self, loggerName=None):
#         super(QAbstractServer, self).__init__()
#         if loggerName:
#             self.__logger = logging.getLogger(loggerName)
#         else:
#             self.__logger = logging.getLogger(self.__class__.__name__)
#         self.__ip = None
#         self.__port = None
#
#         self.__devices = []
#         self.__deviceModel = Device
#
#         self.__handler = None
#         self.__handler_thread = None
#         self.__handlerClass = None
#         self.__server = None
#
#     @Slot(str, int, bytes)
#     def start(self, ip: str, port: int):
#         """Start server."""
#         if self.__handlerClass:
#             ip = QHostAddress(ip)
#             self.__ip = ip
#             self.__port = port
#             self.__handler = self.__handlerClass()
#             self.__handler_thread = QThread()
#             self.__handler.moveToThread(self.__handler_thread)
#
#             self.__handler.connected.connect(self.__on_handler_successful_connection)
#             self.__handler.message.connect(self.__on_handler_device_message)
#             self.__handler.error.connect(self.__on_handler_device_error)
#             self.__handler.disconnected.connect(self.__on_handler_device_disconnected)
#             self.__handler.closed.connect(self.on_closed)
#
#             self.__handler_thread.started.connect(self.__handler.start)
#             self.__handler.started.connect(self.__setup_server)
#             self.__handler_thread.start()
#         else:
#             raise Exception("Handler class not set!")
#
#     @Slot()
#     def __setup_server(self):
#         """Create QTCPServer, start listening for connections."""
#         self.__server = TCPServer()
#         self.__server.connection.connect(self.__handler.on_incoming_connection)
#         if self.__server.listen(self.__ip, self.__port):
#             self.__logger.info("Started listening for connections")
#         else:
#             e = self.__server.errorString()
#             self.__logger.error(e)
#             self.server_error.emit(e)
#
#     @Slot(int, str, int)
#     def __on_handler_successful_connection(self, device_id, ip, port):
#         """When client connects to server successfully."""
#         device = self.__deviceModel(self, device_id, ip, port)
#         self.__devices.append(device)
#         self.__logger.info("Added new CLIENT-{} with address {}:{}".format(device_id, ip, port))
#         self.on_connected(device, ip, port)
#
#     @Slot(int, bytes)
#     def __on_handler_device_message(self, device_id: int, message: bytes):
#         """When server receives message from bot."""
#         self.on_message(self.get_client_by_id(device_id), message)
#
#     @Slot(int)
#     def __on_handler_device_disconnected(self, device_id):
#         """When bot disconnects from server."""
#         device = self.get_client_by_id(device_id)
#         device.set_connected(False)
#         if device in self.__devices:
#             self.__devices.remove(device)
#         self.on_disconnected(device)
#
#     @Slot(int, str)
#     def __on_handler_device_error(self, device_id, error):
#         self.on_error(self.get_client_by_id(device_id), error)
#
#     @Slot(Device, str, int)
#     def on_connected(self, device: Device, ip: str, port: int):
#         """Called when new client connects to server.
#         Emits connected signal.
#
#         Args:
#             device (Device): Device object.
#             ip (str): Client ip address.
#             port (int): Client port.
#         """
#         self.connected.emit(device, ip, port)
#
#     @Slot(Device, bytes)
#     def on_message(self, device: Device, message: bytes):
#         """Called when server receives message from client.
#         Emits message signal.
#
#         Args:
#             device (Device): Message sender.
#             message (bytes): Message.
#         """
#         self.message.emit(device, message)
#
#     @Slot(Device)
#     def on_disconnected(self, device: Device):
#         """Called when device disconnects from server.
#         Emits disconnected signal.
#
#         Args:
#             device (Device): Disconnected device.
#         """
#         self.disconnected.emit(device)
#
#     @Slot(Device, str)
#     def on_error(self, device: Device, error: str):
#         """Called when a socket error occurs.
#         Emits error signal.
#
#         Args:
#             device (Device): Device object.
#             error (str): Error string.
#         """
#         self.error.emit(device, error)
#
#     @Slot()
#     def on_closed(self):
#         self.closed.emit()
#
#     @Slot(Device, bytes)
#     def write(self, device: Device, data: bytes):
#         """Write data to device."""
#         if not self.__server or not self.__handler:
#             raise ServerNotRunning("Server is not running")
#         if not device.is_connected():
#             raise NotConnectedError("Client is not connected")
#         self.__handler.write.emit(device.id(), data)
#
#     @Slot(bytes)
#     def write_all(self, data: bytes):
#         """Write data to all clients."""
#         if not self.__server or not self.__handler:
#             raise ServerNotRunning("Server is not running")
#         self.__handler.write_all.emit(data)
#
#     @Slot()
#     def kick(self, device: Device):
#         """Disconnect device from server."""
#         if not self.__server or not self.__handler:
#             raise ServerNotRunning("Server is not running")
#         if not device.is_connected():
#             raise NotConnectedError("Client is not connected")
#         self.__handler.kick.emit(device.id())
#
#     @Slot()
#     def close(self):
#         """Disconnect clients and close server."""
#         self.__logger.info("Closing server...")
#         if self.__server:
#             self.__server.close()
#         if self.__handler:
#             self.__handler.close()
#             self.__handler_thread.quit()
#
#     def set_device_model(self, model):
#         """Set model to use for device when client connects.
#
#         Note:
#             Model should be subclassing Device.
#         """
#         if self.is_running():
#             raise Exception("Set device model before starting server!")
#
#         if not issubclass(model, Device):
#             raise ValueError("Model should be subclassing Device class.")
#
#         try:
#             model(QAbstractServer(), 0, "127.0.0.1", 5000)
#         except TypeError as e:
#             raise TypeError("Model is not valid class! Exception: {}".format(e))
#
#         self.__deviceModel = model
#
#     def is_running(self):
#         """Check if server is running."""
#         if self.__handler_thread:
#             return self.__handler_thread.isRunning()
#         return False
#
#     def wait(self):
#         """Wait for server thread to close."""
#         if self.__handler_thread:
#             return self.__handler_thread.wait()
#         return True
#
#     @Slot(int)
#     def get_client_by_id(self, device_id: int) -> Device:
#         """Returns device with associated ID.
#
#         Args:
#             device_id (int): Device ID.
#         """
#         for device in self.__devices:
#             if device.id() == device_id:
#                 return device
#         raise Exception("CLIENT-{} not found".format(device_id))
#
#     def get_devices(self):
#         """Returns list with clients."""
#         return self.__devices
#
#     def set_handler_class(self, handler):
#         """Set handler to use. This should not be used
#         outside this library."""
#         if self.is_running():
#             raise Exception("Set socket handler before starting server!")
#         try:
#             handler()
#         except TypeError as e:
#             raise TypeError("Handler is not valid class! Exception: {}".format(e))
#         self.__handlerClass = handler
