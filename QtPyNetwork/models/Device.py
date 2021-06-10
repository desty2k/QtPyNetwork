from qtpy.QtCore import QObject, Slot, Signal

import ipaddress

from QtPyNetwork.exceptions import NotConnectedError


class Device(QObject):
    """Represents psychical device connected to server."""
    _write = Signal(bytes)
    _kick = Signal()

    def __init__(self, device_id: int, ip: str, port: int):
        super(Device, self).__init__(None)
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError("Device's IP address is not valid!")

        if not 1 <= port <= 65535:
            raise ValueError("Port must be in range 1, 65535")

        self.ip = ip
        self.port = port
        self.id = device_id
        self.connected = True

    @Slot()
    def get_id(self):
        return self.id

    @Slot(bool)
    def set_connected(self, value: bool):
        self.connected = value

    @Slot()
    def is_connected(self):
        return self.connected

    @Slot()
    def kick(self):
        if self.connected:
            self._kick.emit()
        else:
            raise NotConnectedError("Client is not connected")

    @Slot(bytes)
    def write(self, message):
        if self.connected:
            self._write.emit(message)
        else:
            raise NotConnectedError("Client is not connected")
