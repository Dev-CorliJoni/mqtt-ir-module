#!/usr/bin/env python3
import signal
import threading
from typing import Optional

from agents import LocalAgent, LocalTransport
from connections import (
    AgentBindingStore,
    AgentCommandHandler,
    PairingManagerAgent,
    RuntimeLoader,
)
from electronics.ir_ctl_engine import IrCtlEngine
from electronics.ir_signal_parser import IrSignalParser
from helper import Environment, SettingsCipher
from database import Database
from runtime_version import SOFTWARE_VERSION

env = Environment()
database = Database(data_dir=env.data_folder)
settings_cipher = SettingsCipher(env.settings_master_key)
binding_store = AgentBindingStore(settings_store=database.settings)
parser = IrSignalParser()
engine = IrCtlEngine(
    ir_rx_device=env.ir_rx_device,
    ir_tx_device=env.ir_tx_device,
    wideband_default=env.ir_wideband,
)
local_transport = LocalTransport(engine=engine, parser=parser)
local_agent = LocalAgent(transport=local_transport, agent_id="local-agent-runtime", name="Local Agent Runtime")

runtime_loader = RuntimeLoader(
    settings_store=database.settings,
    settings_cipher=settings_cipher,
    role="agent",
    environment=env,
)
pairing_manager = PairingManagerAgent(
    runtime_loader=runtime_loader,
    binding_store=binding_store,
    readable_name="IR Agent",
    sw_version=SOFTWARE_VERSION,
    can_send=True,
    can_learn=True,
    reset_binding=env.agent_pairing_reset,
)
command_handler = AgentCommandHandler(
    runtime_loader=runtime_loader,
    binding_store=binding_store,
    local_agent=local_agent,
)
_shutdown_event = threading.Event()


def _handle_shutdown_signal(signum: int, frame: Optional[object]) -> None:
    _shutdown_event.set()


def run() -> int:
    database.init()
    runtime_loader.start()
    pairing_manager.start()
    command_handler.start()
    try:
        while not _shutdown_event.wait(timeout=1.0):
            pass
        return 0
    finally:
        command_handler.stop()
        pairing_manager.stop()
        runtime_loader.stop()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)
    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    raise SystemExit(run())
