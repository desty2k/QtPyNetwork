from qtpy.QtCore import QObject, Slot, Signal

import ipaddress

from QtPyNetwork.exceptions import NotConnectedError


class Device(QObject):
    """Represents psychical device connected to server."""

    def __init__(self, server, device_id: int, ip: str, port: int):
        super(Device, self).__init__(None)
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError("Device's IP address is not valid!")

        if not 1 <= port <= 65535:
            raise ValueError("Port must be in range 1, 65535")

        self.__ip = ip
        self.__port = port
        self.__id = device_id
        self.__connected = True
        self.__server = server

    @Slot()
    def server(self):
        return self.__server

    @Slot()
    def id(self):
        return self.__id

    @Slot()
    def ip(self):
        return self.__ip

    @Slot()
    def port(self):
        return self.__port

    @Slot(bool)
    def set_connected(self, value: bool):
        self.__connected = value

    @Slot()
    def is_connected(self) -> bool:
        return self.__connected

    @Slot()
    def kick(self):
        self.server().kick(self)

    @Slot(bytes)
    def write(self, message: bytes):
        self.server().write(self, message)
