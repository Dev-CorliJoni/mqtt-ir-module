# app/electronics/ir_receiver.py
import subprocess
import threading
import time
from typing import Optional

from helper.database import Database


class IRReceiver:
    def __init__(self, store: Database) -> None:
        self._database = store

        self._proc: Optional[subprocess.Popen[str]] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._lock = threading.Lock()
        self._learn_enabled = False
        self._learn_device_name: Optional[str] = None
        self._learn_expires_at: Optional[float] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="ir-receiver", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._terminate_proc()
        if self._thread:
            self._thread.join(timeout=2)

    def enable_learning(self, device_name: str, timeout_s: int) -> None:
        # Start receiver only when learning is enabled
        self.start()
        with self._lock:
            self._learn_enabled = True
            self._learn_device_name = device_name
            self._learn_expires_at = time.time() + timeout_s

    def disable_learning(self) -> None:
        with self._lock:
            self._learn_enabled = False
            self._learn_device_name = None
            self._learn_expires_at = None
        # Stop receiver when learning is disabled
        self.stop()

    def is_learning(self) -> bool:
        with self._lock:
            return self._learn_enabled and (self._learn_expires_at is None or time.time() < self._learn_expires_at)

    def learn_device_name(self) -> Optional[str]:
        with self._lock:
            return self._learn_device_name

    def learn_expires_at(self) -> Optional[float]:
        with self._lock:
            return self._learn_expires_at

    def _terminate_proc(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=1)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None

    def _run_loop(self) -> None:
        """
        Reads decoded IR events from lircd via `irw`.
        Typical irw line format:
          <hex> <repeat> <key_name> <remote_name>
        """
        while not self._stop_event.is_set():
            try:
                self._proc = subprocess.Popen(
                    ["irw"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert self._proc.stdout is not None

                for line in self._proc.stdout:
                    if self._stop_event.is_set():
                        break

                    line = line.strip()
                    if not line:
                        continue

                    # Auto-timeout handling
                    with self._lock:
                        if self._learn_enabled and self._learn_expires_at is not None and time.time() >= self._learn_expires_at:
                            self._learn_enabled = False
                            self._learn_device_name = None
                            self._learn_expires_at = None
                            # Stop receiver after timeout
                            self._stop_event.set()
                            break

                        learn_enabled = self._learn_enabled
                        device_name = self._learn_device_name

                    if learn_enabled and device_name:
                        self._database.add_learned_code(device_name=device_name, code_value=line)

                self._terminate_proc()
            except Exception:
                self._terminate_proc()
                time.sleep(0.5)
                
                