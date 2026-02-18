#!/usr/bin/env python3
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, APIRouter

from agents import LocalAgent, LocalTransport
from agents.agent_id_store import get_or_create_agent_id
from electronics.ir_ctl_engine import IrCtlEngine
from electronics.ir_signal_parser import IrSignalParser
from helper import Environment, SettingsCipher
from helper.hub_connections import HubConnections
from database import Database

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
hub_connections = HubConnections(
    settings_store=database.settings,
    settings_cipher=settings_cipher,
    role="agent",
    enable_homeassistant=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init()
    hub_connections.start()
    try:
        yield
    finally:
        hub_connections.stop()

app = FastAPI(
    title="mqtt-ir-agent",
    version="0.1.0",
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
    return hub_connections.status()


app.include_router(api)
