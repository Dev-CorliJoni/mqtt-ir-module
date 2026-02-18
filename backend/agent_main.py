#!/usr/bin/env python3
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, APIRouter

from agents import LocalAgent, LocalTransport
from agents.agent_id_store import get_or_create_agent_id
from connections import PairingManagerAgent, RuntimeLoader
from electronics.ir_ctl_engine import IrCtlEngine
from electronics.ir_signal_parser import IrSignalParser
from helper import Environment, SettingsCipher
from database import Database
from runtime_version import SOFTWARE_VERSION

env = Environment()
database = Database(data_dir=env.data_folder)
settings_cipher = SettingsCipher(env.settings_master_key)

parser = IrSignalParser()
engine = IrCtlEngine(
    ir_rx_device=env.ir_rx_device,
    ir_tx_device=env.ir_tx_device,
    wideband_default=env.ir_wideband,
)
local_transport = LocalTransport(engine=engine, parser=parser)
local_agent_id = get_or_create_agent_id(data_dir=env.data_folder)
local_agent = LocalAgent(transport=local_transport, agent_id=local_agent_id)
runtime_loader = RuntimeLoader(
    settings_store=database.settings,
    settings_cipher=settings_cipher,
    role="agent",
)
pairing_manager = PairingManagerAgent(
    runtime_loader=runtime_loader,
    settings_store=database.settings,
    agent_uid=local_agent.agent_id,
    readable_name=local_agent.name,
    sw_version=SOFTWARE_VERSION,
    can_send=True,
    can_learn=bool(local_agent.capabilities.get("canLearn")),
    reset_binding=env.agent_pairing_reset,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init()
    runtime_loader.start()
    pairing_manager.start()
    try:
        yield
    finally:
        pairing_manager.stop()
        runtime_loader.stop()

app = FastAPI(
    title="mqtt-ir-agent",
    version=SOFTWARE_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

api = APIRouter(prefix="/api")


@api.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True}


@api.get("/status/electronics")
def agent_electronics_status() -> Dict[str, Any]:
    return {
        "ir_rx_device": env.ir_rx_device,
        "ir_tx_device": env.ir_tx_device,
        "debug": env.debug,
    }


@api.get("/status/agent")
def agent_status() -> Dict[str, Any]:
    return local_agent.get_status()


@api.get("/status/mqtt")
def agent_mqtt_status() -> Dict[str, Any]:
    return runtime_loader.status()


@api.get("/status/pairing")
def agent_pairing_status() -> Dict[str, Any]:
    return pairing_manager.status()


app.include_router(api)
