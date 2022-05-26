from qtpy.QtNetwork import QAbstractSocket
from struct import unpack, calcsize, pack

HEADER = '!L'
HEADER_SIZE = calcsize(HEADER)


def read(socket: QAbstractSocket, buffer: bytes, size_left: int) -> (bytes, int):
    """Read data from socket.

    Args:
        socket (QAbstractSocket): Socket to read from.
        buffer (bytes): Buffer to read into.
        size_left (int): Size left to read.

    Returns:
        bytes: Read data.
    """
    while socket.bytesAvailable():
        print(f"Reading {size_left} bytes with buffer {buffer}")
        if size_left > 0:
            data = socket.read(size_left)
            size_left = size_left - len(data)
            if size_left > 0:
                buffer += data
            else:
                return buffer + data, 0
        else:
            header = socket.read(HEADER_SIZE)
            data_size = unpack(HEADER, header)[0]
            data = socket.read(data_size)
            if len(data) < data_size:
                buffer = data
                size_left = data_size
            else:
                return data, 0


def write(socket: QAbstractSocket, data: bytes) -> None:
    """Write data to socket.

    Args:
        socket (QAbstractSocket): Socket to write to.
        data (bytes): Data to write.
    """
    print(f"Writing {len(data)} bytes with buffer {data}")
    data = pack(HEADER, len(data)) + data
    socket.write(data)
