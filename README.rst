QtPyNetwork
===========

|Build Status| |Docs Status|  |PyPI Downloads|

QtPyNetwork is a small abstraction layer for sending and receiving messages using TCP sockets.

`Check out the complete documentation. <https://desty2k.github.io/QtPyNetwork/readme.html>`__

Features
--------

- every data write and read call is executed inside thread
- signals for each event - connected, disconnected, error, etc.

There are two servers available:

- QBalancedServer
- QThreadedServer

The first one has constant amount of threads.
When new client connects, server checks which worker has the least amount of active sockets and passes socket
descriptor to that thread. QThreadedServer creates new thread for each connected device.

QThreadedClient is socket client, that keeps socket in separate thread.

Usage
-----

See examples directory for client and server code samples.
You can use both composition and inheritance to create client and server.

Client
~~~~~~


.. code-block:: python

    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QObject, Slot, QCoreApplication

    import sys
    import logging

    from QtPyNetwork.client import QThreadedClient

    IP, PORT = "127.0.0.1", 12500


    class Main(QObject):

        def __init__(self):
            super(Main, self).__init__(None)

        def setup(self):
            self.logger = logging.getLogger(self.__class__.__name__)

            self.cln = QThreadedClient()
            self.cln.message.connect(self.on_message)
            self.cln.failed_to_connect.connect(self.close)
            self.cln.disconnected.connect(self.close)
            self.cln.start(IP, PORT)

        @Slot(bytes)
        def on_message(self, data: bytes):
            self.logger.info(data)

        @Slot()
        def close(self):
            self.cln.close()
            while self.cln.is_running():
                self.cln.wait()
            QApplication.instance().quit()


    if __name__ == '__main__':
        logging.basicConfig(level=logging.NOTSET)
        app = QCoreApplication(sys.argv)

        main = Main()
        main.setup()
        sys.exit(app.exec_())


Server
~~~~~~

.. code-block:: python

    from qtpy.QtCore import QObject, Slot, QCoreApplication

    import sys
    import logging

    from QtPyNetwork.server import QBalancedServer
    from QtPyNetwork.models import Device

    IP, PORT = "127.0.0.1", 12500


    class Main(QBalancedServer):

        def __init__(self):
            super(Main, self).__init__(None)
            self.logger = logging.getLogger(self.__class__.__name__)

        @Slot(Device)
        def on_connected(device: Device):
            self.logger.info("New device connected: {}".format(device.id()))

        @Slot(Device, bytes)
        def on_message(self, device: Device, message: bytes):
            self.logger.info("Received from {}: {}".format(device.id(), message))

        @Slot(Device)
        def on_disconnected(self, device: Device):
            self.logger.info("Device {} disconnected".format(device.id()))
            self.close()

    if __name__ == '__main__':
        logging.basicConfig(level=logging.NOTSET)
        app = QCoreApplication(sys.argv)
        main = Main()
        main.start(IP, PORT)
        sys.exit(app.exec_())

.. |Docs Status| image:: https://github.com/desty2k/QtPyNetwork/workflows/docs/badge.svg
   :target: https://desty2k.github.io/QtPyNetwork/
.. |Build Status| image:: https://github.com/desty2k/QtPyNetwork/actions/workflows/build.yml/badge.svg
   :target: https://github.com/desty2k/QtPyNetwork/actions/workflows/build.yml
.. |PyPI Downloads| image:: https://img.shields.io/pypi/dm/qtpynetwork
   :target: https://pypi.org/project/QtPyNetwork/
