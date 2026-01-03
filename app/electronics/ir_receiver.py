import os
import shutil
import signal
import subprocess
import threading
import time
from typing import Optional, Callable

from helper.database import Database
from electronics.models import LearnSession


class IRReceiver:
    def __init__(
        self,
        store: Database,
        ir_device: str,
        data_dir: str,
        stop_lircd: Callable[[], None],
        start_lircd: Callable[[], None],
    ) -> None:
        self._db = store
        self._ir_device = ir_device
        self._data_dir = data_dir
        self._stop_lircd = stop_lircd
        self._start_lircd = start_lircd

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._proc: Optional[subprocess.Popen[str]] = None
        self._session: Optional[LearnSession] = None

    @property
    def is_learning(self) -> bool:
        with self._lock:
            if not self._session:
                return False
            if time.time() >= self._session.expires_at:
                return False
            return self._thread is not None and self._thread.is_alive()

    @property
    def device_id(self) -> Optional[int]:
        with self._lock:
            return self._session.device_id if self._session else None

    @property
    def device_name(self) -> Optional[str]:
        with self._lock:
            return self._session.device_name if self._session else None

    @property
    def lirc_name(self) -> Optional[str]:
        with self._lock:
            return self._session.lirc_name if self._session else None

    @property
    def expires_at(self) -> Optional[float]:
        with self._lock:
            return self._session.expires_at if self._session else None

    def start_learning(self, device_id: int, device_name: str, lirc_name: str, timeout_s: int) -> None:
        if timeout_s <= 0:
            raise ValueError("timeout_s must be > 0")

        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("Learning is already running")

            expires_at = time.time() + timeout_s

            data_dir = os.path.join(self._data_dir, "lirc", "remotes")
            os.makedirs(data_dir, exist_ok=True)

            data_conf = os.path.join(data_dir, f"{lirc_name}.conf")
            etc_conf = os.path.join("/etc/lirc/lircd.conf.d", f"{lirc_name}.conf")

            self._session = LearnSession(
                device_id=device_id,
                device_name=device_name,
                lirc_name=lirc_name,
                expires_at=expires_at,
                data_conf_path=data_conf,
                etc_conf_path=etc_conf,
            )
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_irrecord, name="ir-learn-irrecord", daemon=True)

        self._stop_lircd()
        self._thread.start()

    def stop_learning(self) -> None:
        with self._lock:
            self._stop_event.set()
            proc = self._proc

        if proc and proc.poll() is None:
            try:
                proc.send_signal(signal.SIGINT)
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass

        with self._lock:
            t = self._thread

        if t:
            t.join(timeout=10)

        with self._lock:
            self._proc = None
            self._thread = None
            self._session = None

        self._start_lircd()

    def _run_irrecord(self) -> None:
        with self._lock:
            session = self._session
        if not session:
            return

        self._clean_previous(session)

        button_idx = 1
        pending_button: Optional[str] = None
        finish_requested = False

        args = ["irrecord", "-f", "-n", "-d", self._ir_device, session.data_conf_path]

        proc: Optional[subprocess.Popen[str]] = None

        def send_line(text: str) -> None:
            if proc is None or proc.stdin is None:
                return
            proc.stdin.write(text + "\n")
            proc.stdin.flush()

        try:
            proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            with self._lock:
                self._proc = proc

            assert proc.stdout is not None

            for raw in proc.stdout:
                now = time.time()
                if now >= session.expires_at:
                    finish_requested = True
                if self._stop_event.is_set():
                    finish_requested = True

                low = raw.strip().lower()

                if "press return to continue" in low or "press enter to continue" in low:
                    send_line("")
                    continue

                if "name of the remote control" in low:
                    send_line(session.lirc_name)
                    continue

                if "please enter the name for the next button" in low:
                    if pending_button:
                        self._db.create_code(device_id=session.device_id, code_value=pending_button)
                        pending_button = None
                        self._mirror_to_etc(session)

                    if finish_requested:
                        send_line("")
                        continue

                    next_name = f"BTN_{button_idx:04d}"
                    button_idx += 1
                    pending_button = next_name
                    send_line(next_name)
                    continue

            try:
                proc.wait(timeout=5)
            except Exception:
                pass

        finally:
            try:
                self._mirror_to_etc(session)
            except Exception:
                pass

            with self._lock:
                self._proc = None
                self._thread = None
                self._session = None

            self._start_lircd()

    def _clean_previous(self, session: LearnSession) -> None:
        self._db.clear_codes_for_device(session.device_id)

        for p in (session.data_conf_path, session.etc_conf_path):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

    def _mirror_to_etc(self, session: LearnSession) -> None:
        os.makedirs(os.path.dirname(session.etc_conf_path), exist_ok=True)
        if os.path.exists(session.data_conf_path):
            shutil.copyfile(session.data_conf_path, session.etc_conf_path)

