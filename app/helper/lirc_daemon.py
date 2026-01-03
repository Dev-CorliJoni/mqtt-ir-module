import os
import subprocess
import threading
from typing import Optional


class LircDaemonManager:
    def __init__(self, config_path: str = "/etc/lirc/lirc_options.conf") -> None:
        self._config_path = config_path
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen[str]] = None

    def start(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return

            os.makedirs("/var/run/lirc", exist_ok=True)

            # Use lirc_options.conf; it references output socket etc.
            self._proc = subprocess.Popen(
                ["lircd", "--nodaemon", "--options-file", self._config_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )

    def stop(self) -> None:
        with self._lock:
            if not self._proc or self._proc.poll() is not None:
                self._proc = None
                return

            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass

            self._proc = None
            