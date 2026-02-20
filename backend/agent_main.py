#!/usr/bin/env python3
import signal
import threading
from typing import Optional

from connections import PairingManagerAgent, RuntimeLoader
from helper import Environment, SettingsCipher
from database import Database
from runtime_version import SOFTWARE_VERSION

env = Environment()
database = Database(data_dir=env.data_folder)
settings_cipher = SettingsCipher(env.settings_master_key)

runtime_loader = RuntimeLoader(
    settings_store=database.settings,
    settings_cipher=settings_cipher,
    role="agent",
    environment=env,
)
pairing_manager = PairingManagerAgent(
    runtime_loader=runtime_loader,
    settings_store=database.settings,
    readable_name="IR Agent",
    sw_version=SOFTWARE_VERSION,
    can_send=True,
    can_learn=True,
    reset_binding=env.agent_pairing_reset,
)
_shutdown_event = threading.Event()


def _handle_shutdown_signal(signum: int, frame: Optional[object]) -> None:
    _shutdown_event.set()


def run() -> int:
    database.init()
    runtime_loader.start()
    pairing_manager.start()
    try:
        while not _shutdown_event.wait(timeout=1.0):
            pass
        return 0
    finally:
        pairing_manager.stop()
        runtime_loader.stop()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)
    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    raise SystemExit(run())
