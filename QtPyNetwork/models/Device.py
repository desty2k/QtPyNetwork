from qtpy.QtCore import QObject, Slot, Signal

import ipaddress


class Device(QObject):
    """Represents psychical device connected to server."""
    _write = Signal(int, dict)

    def __init__(self, device_id: int, ip: str, port: int):
        super(Device, self).__init__(None)
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError("Device's IP address is not valid!")

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

    @Slot(dict)
    def write(self, message):
        self._write.emit(self.id, message)
