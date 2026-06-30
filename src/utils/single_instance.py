"""Single-instance guard + activation over a loopback socket.

The first instance binds a fixed loopback port; a later launch fails to bind,
pings the running instance to surface its window, and exits.
"""
import logging
import socket
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)

_HOST = "127.0.0.1"
_PORT = 52317


class SingleInstance:
    """Holds the lock for the running instance and surfaces it on a second launch."""

    def __init__(self) -> None:
        self.on_activate: Callable[[], None] = lambda: None
        self._sock: socket.socket | None = None

    def acquire(self) -> bool:
        """Return True if this is the only instance; else ping the running one and return False."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((_HOST, _PORT))
        except OSError:
            sock.close()
            self._ping()
            return False
        sock.listen()
        self._sock = sock
        threading.Thread(target=self._serve, daemon=True).start()
        return True

    def _ping(self) -> None:
        try:
            with socket.create_connection((_HOST, _PORT), timeout=1) as conn:
                conn.sendall(b"show")
        except OSError:
            pass

    def _serve(self) -> None:
        while self._sock is not None:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            with conn:
                if conn.recv(16) == b"show":
                    self.on_activate()

    def release(self) -> None:
        sock, self._sock = self._sock, None
        if sock is not None:
            sock.close()
