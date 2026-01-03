# app/main.py
#!/usr/bin/env python3
import os
import subprocess
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Header

from api_models import MappingCreate, LearnStart, DeviceCreate
from electronics import IRReceiver
from helper import Environment, Database

env = Environment()


def require_api_key(x_api_key: Optional[str]) -> None:
    if not env.api_key:
        return
    if not x_api_key or x_api_key != env.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def start_lircd() -> subprocess.Popen[str]:
    os.makedirs("/var/run/lirc", exist_ok=True)
    return subprocess.Popen(["lircd", "--nodaemon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)


def stop_process(proc: Optional[subprocess.Popen[str]]) -> None:
    if not proc:
        return
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=2)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


database = Database(data_dir=env.data_folder)
receiver = IRReceiver(store=database)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init()
    lircd_proc = start_lircd()
    try:
        yield
    finally:
        receiver.stop()
        stop_process(lircd_proc)


app = FastAPI(title="mqtt-ir-module", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "ir_device": env.ir_device,
        "learn_enabled": receiver.is_learning(),
        "learn_device": receiver.learn_device_name(),
        "learn_expires_at": receiver.learn_expires_at(),
    }


@app.post("/devices")
def create_device(body: DeviceCreate, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    device = database.create_device(name=body.name)
    return device


@app.get("/devices")
def list_devices() -> List[Dict[str, Any]]:
    return database.list_devices()


@app.post("/learn/start")
def learn_start(body: LearnStart, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    timeout_s = body.timeout_s if body.timeout_s is not None else env.learn_timeout
    if timeout_s <= 0:
        raise HTTPException(status_code=400, detail="timeout_s must be > 0")

    database.create_device(name=body.device_name)
    receiver.enable_learning(device_name=body.device_name, timeout_s=timeout_s)

    return {
        "learn_enabled": True,
        "device_name": body.device_name,
        "expires_at": receiver.learn_expires_at(),
        "timeout_s": timeout_s,
    }


@app.post("/learn/stop")
def learn_stop(x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    receiver.disable_learning()
    return {"learn_enabled": False}


@app.get("/learn/status")
def learn_status() -> Dict[str, Any]:
    return {
        "learn_enabled": receiver.is_learning(),
        "device_name": receiver.learn_device_name(),
        "expires_at": receiver.learn_expires_at(),
    }


@app.get("/codes")
def list_codes(device_name: Optional[str] = None) -> List[Dict[str, Any]]:
    return database.list_codes(device_name=device_name)


@app.get("/codes/recent")
def list_recent_codes(limit: int = 20) -> List[Dict[str, Any]]:
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    return database.list_recent_codes(limit=limit)


@app.post("/mappings")
def create_mapping(body: MappingCreate, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return database.create_mapping(
            device_name=body.device_name,
            action_name=body.action_name,
            code_id=body.code_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/mappings")
def list_mappings(device_name: Optional[str] = None) -> List[Dict[str, Any]]:
    return database.list_mappings(device_name=device_name)

