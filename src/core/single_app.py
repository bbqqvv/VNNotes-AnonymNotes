import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtCore import pyqtSignal, QSharedMemory

logger = logging.getLogger(__name__)

class SingleApplication(QApplication):
    """
    Ensures only a single instance of the application runs at any time.
    If a second instance is launched, it forwards its command-line arguments (like vnnotes:// links)
    to the primary running instance and immediately exits to prevent SQLite locking.
    """
    message_received = pyqtSignal(str)

    def __init__(self, argv, app_id="vnnotes_stable_v3_ipc"):
        super().__init__(argv)
        self.app_id = app_id
        
        # Defensive SharedMemory Check (Handles Windows gracefully)
        self.shared_memory = QSharedMemory(self.app_id)
        if self.shared_memory.attach():
            self._is_running = True
        else:
            self._is_running = not self.shared_memory.create(1)

        self.server = None

        if self._is_running:
            # We are the second instance. Try to send message to the first.
            msg = " ".join(argv[1:]) if len(argv) > 1 else "FOCUS"
            self._send_message(msg)
        else:
            # We are the primary instance. Start listening.
            self.server = QLocalServer(self)
            QLocalServer.removeServer(self.app_id) # Cleanup any dangling socket (unix)
            if self.server.listen(self.app_id):
                self.server.newConnection.connect(self._handle_connection)
                logger.info(f"SingleApplication registered IPC Server on '{self.app_id}'")
            else:
                logger.error(f"Cannot start IPC server: {self.server.errorString()}")

    def is_running(self):
        """Returns True if another instance is already running."""
        return self._is_running

    def _send_message(self, msg):
        socket = QLocalSocket()
        socket.connectToServer(self.app_id)
        if socket.waitForConnected(1000):
            socket.write(msg.encode('utf-8'))
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            # We don't log to file so we avoid writing to the same logfile block
        else:
            pass 

    def _handle_connection(self):
        socket = self.server.nextPendingConnection()
        if socket.waitForReadyRead(1000):
            data = socket.readAll().data().decode('utf-8')
            if data:
                logger.info(f"SingleApplication received IPC string: {data}")
                self.message_received.emit(data)
                
        socket.disconnectFromServer()
        socket.deleteLater()
