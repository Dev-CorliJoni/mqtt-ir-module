#!/usr/bin/env python3
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any

import json

from fastapi import FastAPI, HTTPException, Header, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from api_models import (
    RemoteCreate,
    RemoteUpdate,
    LearnStart,
    LearnCapture,
    ButtonUpdate,
    SendRequest,
    SettingsUpdate,
)
from electronics import IrLearningService, IrSenderService
from electronics.ir_ctl_engine import IrCtlEngine
from electronics.ir_hold_extractor import IrHoldExtractor
from electronics.ir_signal_aggregator import IrSignalAggregator
from electronics.ir_signal_parser import IrSignalParser
from electronics.status_communication import StatusCommunication
from helper import Environment
from database import Database

env = Environment()
database = Database(data_dir=env.data_folder)

parser = IrSignalParser()
aggregator = IrSignalAggregator()
hold_extractor = IrHoldExtractor(aggregator)
engine = IrCtlEngine(ir_device=env.ir_device, wideband_default=env.ir_wideband)
status_comm = StatusCommunication()

learning_defaults = database.settings.get_learning_defaults()
learning = IrLearningService(
    database=database,
    engine=engine,
    parser=parser,
    aggregator=aggregator,
    hold_extractor=hold_extractor,
    debug=env.debug,
    aggregate_round_to_us=learning_defaults["aggregate_round_to_us"],
    aggregate_min_match_ratio=learning_defaults["aggregate_min_match_ratio"],
    hold_idle_timeout_ms=learning_defaults["hold_idle_timeout_ms"],
    status_comm=status_comm,
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
    # Load persisted learning defaults after the settings table exists.
    learning.apply_learning_settings(database.settings.get_learning_settings())
    # Store the running loop so sync code can broadcast status updates.
    status_comm.attach_loop(asyncio.get_running_loop())

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
# Settings (UI)
# -----------------


@api.get("/settings")
def get_settings() -> Dict[str, Any]:
    return database.settings.get_ui_settings()


@api.put("/settings")
def update_settings(body: SettingsUpdate, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    if (
        body.theme is None
        and body.language is None
        and body.press_takes_default is None
        and body.capture_timeout_ms_default is None
        and body.hold_idle_timeout_ms is None
        and body.aggregate_round_to_us is None
        and body.aggregate_min_match_ratio is None
    ):
        raise HTTPException(status_code=400, detail="at least one setting must be provided")
    try:
        updated = database.settings.update_ui_settings(
            theme=body.theme,
            language=body.language,
            press_takes_default=body.press_takes_default,
            capture_timeout_ms_default=body.capture_timeout_ms_default,
            hold_idle_timeout_ms=body.hold_idle_timeout_ms,
            aggregate_round_to_us=body.aggregate_round_to_us,
            aggregate_min_match_ratio=body.aggregate_min_match_ratio,
        )
        learning.apply_learning_settings(updated)
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------
# Remotes CRUD
# -----------------


@api.post("/remotes")
def create_remote(body: RemoteCreate, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return database.remotes.create(name=body.name, icon=body.icon)
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
            icon=body.icon,
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
        return database.buttons.rename(button_id=button_id, name=body.name, icon=body.icon)
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

    learning_settings = database.settings.get_learning_settings()
    learning.apply_learning_settings(learning_settings)
    takes = body.takes if body.takes is not None else learning_settings["press_takes_default"]
    timeout_ms = body.timeout_ms if body.timeout_ms is not None else learning_settings["capture_timeout_ms_default"]

    try:
        return learning.capture(
            remote_id=body.remote_id,
            mode=body.mode,
            takes=takes,
            timeout_ms=timeout_ms,
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


@api.websocket("/learn/status/ws")
async def learn_status_ws(websocket: WebSocket) -> None:
    # Stream status updates over a single WebSocket to avoid frequent polling.
    await status_comm.connect(websocket)
    try:
        await status_comm.send(websocket, learning.status())
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        pass
    finally:
        await status_comm.disconnect(websocket)


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


# Register API at /api
app.include_router(api)

# Optional: also register the same API under the public base url (so direct /base/api works without a proxy)
public_base_url = env.public_base_url  # always with trailing slash
base_prefix = public_base_url.rstrip("/")
if base_prefix:
    app.include_router(api, prefix=base_prefix)

# -----------------
# Frontend (Vite build)
# -----------------

static_dir = Path(__file__).parent / "static"
assets_dir = static_dir / "assets"
index_html = static_dir / "index.html"


def _render_index_html() -> str:
    if not index_html.exists():
        raise HTTPException(status_code=404, detail="Frontend not built (missing static/index.html)")

    html = index_html.read_text(encoding="utf-8", errors="replace")

    api_base = f"{public_base_url.rstrip('/')}/api"
    config = {
        "publicBaseUrl": public_base_url,
        "apiBaseUrl": api_base,
        "publicApiKey": env.public_api_key or "",
        "writeRequiresApiKey": bool(env.api_key),
    }

    # Replace placeholders (frontend/index.html contains these markers before build)
    html = html.replace("__PUBLIC_BASE_URL__", public_base_url)
    html = html.replace("__APP_CONFIG_JSON__", json.dumps(config))

    return html


if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    if base_prefix:
        app.mount(f"{base_prefix}/assets", StaticFiles(directory=assets_dir), name="assets_base")


@app.get("/")
def frontend_index():
    return HTMLResponse(_render_index_html())


@app.get("/{path:path}")
def frontend_fallback(path: str):
    file_path = static_dir / path
    if file_path.is_file():
        return FileResponse(file_path)
    return HTMLResponse(_render_index_html())
