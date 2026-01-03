#!/usr/bin/env python3
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Header

from api_models import LearnStart, Device, Code
from electronics import IRReceiver
from helper import Environment, Database, LircDaemonManager

env = Environment()

database = Database(data_dir=env.data_folder)
lirc = LircDaemonManager()

receiver = IRReceiver(
    store=database,
    ir_device=env.ir_device,
    data_dir=env.data_folder,
    stop_lircd=lirc.stop,
    start_lircd=lirc.start,
)


def require_api_key(x_api_key: Optional[str]) -> None:
    if not env.api_key:
        return
    if not x_api_key or x_api_key != env.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init()
    lirc.start()
    try:
        yield
    finally:
        receiver.stop_learning()
        lirc.stop()


app = FastAPI(title="mqtt-ir-module", version="0.2.0", lifespan=lifespan)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "ir_device": env.ir_device,
        "learn_enabled": receiver.is_learning,
        "learn_device_id": receiver.device_id,
        "learn_device": receiver.device_name,
        "learn_lirc_name": receiver.lirc_name,
        "learn_expires_at": receiver.expires_at,
    }


@app.post("/devices")
def create_device(body: Device, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    return database.create_device(name=body.name)


@app.get("/devices")
def list_devices() -> List[Dict[str, Any]]:
    return database.list_devices()


@app.put("/devices/{device_id}")
def rename_device(device_id: int, body: Device, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return database.rename_device(device_id=device_id, name=body.name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/devices/{device_id}")
def delete_device(device_id: int, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        device = database.get_device(device_id=device_id)
        lirc_name = str(device["lirc_name"])
        deleted = database.delete_device(device_id=device_id)

        data_conf = f"{env.data_folder}/lirc/remotes/{lirc_name}.conf"
        etc_conf = f"/etc/lirc/lircd.conf.d/{lirc_name}.conf"

        for p in (data_conf, etc_conf):
            try:
                import os
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

        return deleted
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/learn/start")
def learn_start(body: LearnStart, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    timeout_s = body.timeout_s if body.timeout_s is not None else env.learn_timeout
    if timeout_s <= 0:
        raise HTTPException(status_code=400, detail="timeout_s must be > 0")

    device = database.create_device(name=body.device_name)
    device_id = int(device["id"])
    lirc_name = str(device["lirc_name"])

    try:
        receiver.start_learning(
            device_id=device_id,
            device_name=str(device["name"]),
            lirc_name=lirc_name,
            timeout_s=timeout_s,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"learn_enabled": True, "device_id": device_id, "expires_at": receiver.expires_at}


@app.post("/learn/stop")
def learn_stop(x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    receiver.stop_learning()
    return {"learn_enabled": False}


@app.get("/learn/status")
def learn_status() -> Dict[str, Any]:
    device_id = receiver.device_id
    codes: List[Dict[str, Any]] = []
    if device_id is not None:
        codes = database.list_codes(device_id=device_id)

    return {
        "learn_enabled": receiver.is_learning,
        "device_id": device_id,
        "device_name": receiver.device_name,
        "lirc_name": receiver.lirc_name,
        "expires_at": receiver.expires_at,
        "codes": codes,
    }


@app.get("/codes")
def list_codes(device_id: Optional[int] = None) -> List[Dict[str, Any]]:
    return database.list_codes(device_id=device_id)


@app.put("/codes/{code_id}")
def update_code(code_id: int, body: Code, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return database.update_code(code_id=code_id, action_name=body.action_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/codes/{code_id}")
def delete_code(code_id: int, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return database.delete_code(code_id=code_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))