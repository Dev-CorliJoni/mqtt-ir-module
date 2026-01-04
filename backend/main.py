#!/usr/bin/env python3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Header, APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api_models import (
    RemoteCreate,
    RemoteUpdate,
    LearnStart,
    LearnCapture,
    ButtonUpdate,
    SendRequest,
)
from electronics import IrLearningService, IrSenderService
from electronics.ir_ctl_engine import IrCtlEngine
from electronics.ir_hold_extractor import IrHoldExtractor
from electronics.ir_signal_aggregator import IrSignalAggregator
from electronics.ir_signal_parser import IrSignalParser
from helper import Environment
from database import Database

env = Environment()
database = Database(data_dir=env.data_folder)

parser = IrSignalParser()
aggregator = IrSignalAggregator()
hold_extractor = IrHoldExtractor(aggregator)
engine = IrCtlEngine(ir_device=env.ir_device, wideband_default=env.ir_wideband)

learning = IrLearningService(
    database=database,
    engine=engine,
    parser=parser,
    aggregator=aggregator,
    hold_extractor=hold_extractor,
    debug=env.debug,
    aggregate_round_to_us=env.aggregate_round_to_us,
    aggregate_min_match_ratio=env.aggregate_min_match_ratio,
    hold_idle_timeout_ms=env.hold_idle_timeout_ms,
)

sender = IrSenderService(store=database, engine=engine, parser=parser)


def require_api_key(x_api_key: Optional[str]) -> None:
    if not env.api_key:
        return
    if not x_api_key or x_api_key != env.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init()

    # Debug capture data can grow quickly; keep it only when DEBUG=true.
    if not env.debug:
        database.captures.clear()

    try:
        yield
    finally:
        learning.stop()


app = FastAPI(
    title="mqtt-ir-module",
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

api = APIRouter(prefix="/api")


@api.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "ir_device": env.ir_device,
        "debug": env.debug,
        "learn_enabled": learning.is_learning,
        "learn_remote_id": learning.remote_id,
        "learn_remote_name": learning.remote_name,
    }


# -----------------
# Remotes CRUD
# -----------------


@api.post("/remotes")
def create_remote(body: RemoteCreate, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return database.remotes.create(name=body.name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.get("/remotes")
def list_remotes() -> List[Dict[str, Any]]:
    return database.remotes.list()


@api.put("/remotes/{remote_id}")
def update_remote(remote_id: int, body: RemoteUpdate, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return database.remotes.update(
            remote_id=remote_id,
            name=body.name,
            carrier_hz=body.carrier_hz,
            duty_cycle=body.duty_cycle,
            gap_us_default=body.gap_us_default,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.delete("/remotes/{remote_id}")
def delete_remote(remote_id: int, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return database.remotes.delete(remote_id=remote_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------
# Buttons CRUD
# -----------------


@api.get("/remotes/{remote_id}/buttons")
def list_buttons(remote_id: int) -> List[Dict[str, Any]]:
    try:
        database.remotes.get(remote_id)
        return database.buttons.list(remote_id=remote_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@api.put("/buttons/{button_id}")
def rename_button(button_id: int, body: ButtonUpdate, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return database.buttons.rename(button_id=button_id, name=body.name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.delete("/buttons/{button_id}")
def delete_button(button_id: int, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return database.buttons.delete(button_id=button_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------
# Learning
# -----------------


@api.post("/learn/start")
def learn_start(body: LearnStart, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return learning.start(remote_id=body.remote_id, extend=body.extend)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.post("/learn/capture")
def learn_capture(body: LearnCapture, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)

    try:
        return learning.capture(
            remote_id=body.remote_id,
            mode=body.mode,
            takes=body.takes,
            timeout_ms=body.timeout_ms,
            overwrite=body.overwrite,
            button_name=body.button_name,
        )
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.post("/learn/stop")
def learn_stop(x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    return learning.stop()


@api.get("/learn/status")
def learn_status() -> Dict[str, Any]:
    return learning.status()


# -----------------
# Sending
# -----------------


@api.post("/send")
def send_ir(body: SendRequest, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)

    if learning.is_learning:
        raise HTTPException(status_code=409, detail="Cannot send while learning is active")

    try:
        return sender.send(button_id=body.button_id, mode=body.mode, hold_ms=body.hold_ms)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

app.include_router(api)

# -----------------
# Frontend (Vite build) at /
# -----------------

static_dir = Path(__file__).parent / "static"
assets_dir = static_dir / "assets"
index_html = static_dir / "index.html"

if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
def frontend_index():
    if index_html.exists():
        return FileResponse(index_html)
    raise HTTPException(status_code=404, detail="Frontend not built (missing static/index.html)")


@app.get("/{path:path}")
def frontend_fallback(path: str):
    file_path = static_dir / path
    if file_path.is_file():
        return FileResponse(file_path)
    if index_html.exists():
        return FileResponse(index_html)
    raise HTTPException(status_code=404, detail="Frontend not built (missing static/index.html)")
