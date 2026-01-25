#!/usr/bin/env python3
from typing import Dict, Any

from fastapi import FastAPI, APIRouter

from agents import LocalAgent, LocalTransport
from agents.agent_id_store import get_or_create_agent_id
from electronics.ir_ctl_engine import IrCtlEngine
from electronics.ir_signal_parser import IrSignalParser
from helper import Environment

env = Environment()

parser = IrSignalParser()
engine = IrCtlEngine(
    ir_rx_device=env.ir_rx_device,
    ir_tx_device=env.ir_tx_device,
    wideband_default=env.ir_wideband,
)
local_transport = LocalTransport(engine=engine, parser=parser)
local_agent_id = get_or_create_agent_id(data_dir=env.data_folder)
local_agent = LocalAgent(transport=local_transport, agent_id=local_agent_id)

app = FastAPI(
    title="mqtt-ir-agent",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

api = APIRouter(prefix="/api")


@api.get("/health")
def health() -> Dict[str, Any]:
    status = local_agent.get_status()
    status.update(
        {
            "ok": True,
            "ir_rx_device": env.ir_rx_device,
            "ir_tx_device": env.ir_tx_device,
            "debug": env.debug,
        }
    )
    return status


@api.get("/status")
def agent_status() -> Dict[str, Any]:
    return local_agent.get_status()


app.include_router(api)
