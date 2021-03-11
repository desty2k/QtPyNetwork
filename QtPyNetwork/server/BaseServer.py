from qtpy.QtCore import Slot, Signal, QObject, QThread
from qtpy.QtNetwork import QTcpServer, QHostAddress


from QtPyNetwork.models import Device

import logging


class TCPServer(QTcpServer):
    """Listens for incoming connections."""
    connection = Signal(int)

    def __init__(self, parent=None):
        super(TCPServer, self).__init__(parent)

    @Slot(int)
    def incomingConnection(self, socket_descriptor):
        self.connection.emit(socket_descriptor)


class QBaseServer(QObject):
    """Server base for QtPyNetwork."""
    connected = Signal(int, str, int)
    message = Signal(int, dict)
    disconnected = Signal(int)
    error = Signal(int, str)
    closed = Signal()

    def __init__(self, loggerName=None):
        super(QBaseServer, self).__init__()
        if loggerName:
            self.__logger = logging.getLogger(loggerName)
        else:
            self.__logger = logging.getLogger(self.__class__.__name__)
        self.__ip = None
        self.__port = None

        self.__devices = []
        self.__deviceModel = Device

        self.__handler = None
        self.__handler_thread = None
        self.__handlerClass = None
        self.__server = None

    @Slot(str, int, bytes)
    def start(self, ip: str, port: int, key: bytes = b""):
        """Start server on IP:Port and decrypt incomming and
        outcomming messages with encryption key."""
        if self.__handlerClass:
            ip = QHostAddress(ip)
            self.__ip = ip
            self.__port = port
            self.__handler = self.__handlerClass(key=key)
            self.__handler_thread = QThread()
            self.__handler.moveToThread(self.__handler_thread)

            self.__handler.connected.connect(self.on_successful_connection)
            self.__handler.message.connect(self.on_message)
            self.__handler.error.connect(self.error.emit)
            self.__handler.disconnected.connect(self.on_device_disconnected)

            self.__handler_thread.started.connect(self.__handler.start)
            self.__handler.started.connect(self.__setup_server)
            self.__handler_thread.start()
        else:
            raise Exception("Handler class not set!")

    @Slot()
    def __setup_server(self):
        """Create QTCPServer, start listening for connections."""
        self.__server = TCPServer()
        self.__server.connection.connect(self.__handler.on_incoming_connection)
        self.__server.listen(self.__ip, self.__port)
        self.__logger.info("Started listening for connections")

    @Slot(int, str, int)
    def on_successful_connection(self, device_id, ip, port):
        """When client connects to server successfully."""
        device = self.__deviceModel(device_id, ip, port)
        self.__devices.append(device)
        self.connected.emit(device_id, ip, port)
        self.__logger.info("Added new CLIENT-{} with address {}:{}".format(device_id, ip, port))

    @Slot(int, dict)
    def on_message(self, device_id: int, message: dict):
        """When server receives message from bot."""
        self.message.emit(device_id, message)

    @Slot(int)
    def on_device_disconnected(self, device_id):
        """When bot disconnects from server."""
        self.__devices.remove(self.getDeviceById(device_id))
        self.disconnected.emit(device_id)

    @Slot(int, dict)
    def write(self, device_id: int, data: dict):
        """Write data to device with specified ID."""
        if not self.__server or not self.__handler:
            self.__logger.error("Start() server before sending data!")
            return
        self.__handler.write.emit(device_id, data)

    @Slot(dict)
    def writeAll(self, data: dict):
        """Write data to all devices."""
        if not self.__server or not self.__handler:
            self.__logger.error("Start() server before sending data!")
            return
        self.__handler.writeAll.emit(data)

    @Slot()
    def close(self):
        """Disconnect clients and close server."""
        self.__logger.info("Closing server...")
        if self.__handler:
            self.__handler.close()
            self.__handler_thread.quit()
        if self.__server:
            self.__server.close()

    def setDeviceModel(self, model):
        """Set model to use for device when client connects.

        Note:
            Model should be subclassing Device.
        """
        if self.isRunning():
            raise Exception("Set device model before starting server!")

        if not issubclass(model, Device):
            raise ValueError("Model should be subclassing Device class.")

        try:
            model(0, "127.0.0.1", 5000)
        except TypeError as e:
            raise TypeError("Model is not valid class! Exception: {}".format(e))

        self.__deviceModel = model

    def isRunning(self):
        """Check if server is running."""
        if self.__handler_thread:
            return self.__handler_thread.isRunning()
        return False

    def wait(self):
        """Wait for server thread to finish."""
        if self.__handler_thread:
            return self.__handler_thread.wait()

    @Slot(int)
    def getDeviceById(self, device_id: int) -> Device:
        """Returns device with associated ID.

        Args:
            device_id (int): Device ID.
        """
        for device in self.__devices:
            if device.get_id() == device_id:
                return device
        raise Exception("CLIENT-{} not found".format(device_id))

    def getDevices(self):
        """Returns list with devices."""
        return self.__devices

    def setHandlerClass(self, handler):
        """Set handler to use. This should not be used
        outside this library."""
        if self.isRunning():
            raise Exception("Set socket handler before starting server!")

        try:
            handler(key=b"")
        except TypeError as e:
            raise TypeError("Handler is not valid class! Exception: {}".format(e))

        self.__handlerClass = handler
