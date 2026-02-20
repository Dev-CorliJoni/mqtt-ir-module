#!/usr/bin/env python3
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Header, APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agents import AgentRegistry, AgentRoutingError, LocalAgent, LocalTransport
from api_models import (
    RemoteCreate,
    RemoteUpdate,
    AgentUpdate,
    PairingOpenRequest,
    LearnStart,
    LearnCapture,
    ButtonUpdate,
    SendRequest,
    SettingsUpdate,
    AgentErrorResponse,
    LearnStartResponse,
    LearnCaptureResponse,
    SendResponse,
)
from electronics import IrLearningService
from electronics.ir_ctl_engine import IrCtlEngine
from electronics.ir_hold_extractor import IrHoldExtractor
from electronics.ir_signal_aggregator import IrSignalAggregator
from electronics.ir_signal_parser import IrSignalParser
from electronics.status_communication import StatusCommunication
from connections import PairingManagerHub, RuntimeLoader
from helper import Environment, SettingsCipher
from database import Database
from runtime_version import SOFTWARE_VERSION

env = Environment()
database = Database(data_dir=env.data_folder)
settings_cipher = SettingsCipher(env.settings_master_key)

parser = IrSignalParser()
aggregator = IrSignalAggregator()
hold_extractor = IrHoldExtractor(aggregator)
engine = IrCtlEngine(
    ir_rx_device=env.ir_rx_device,
    ir_tx_device=env.ir_tx_device,
    wideband_default=env.ir_wideband,
)
status_comm = StatusCommunication()
agent_registry = AgentRegistry(database=database)
local_transport = LocalTransport(engine=engine, parser=parser)
local_agent = LocalAgent(transport=local_transport, agent_id="local-hub-agent")
runtime_loader = RuntimeLoader(
    settings_store=database.settings,
    settings_cipher=settings_cipher,
    role="hub",
    environment=env,
)
pairing_manager = PairingManagerHub(
    runtime_loader=runtime_loader,
    database=database,
    sw_version=SOFTWARE_VERSION,
    auto_open=False,
)

learning_defaults = database.settings.get_learning_defaults()
learning = IrLearningService(
    database=database,
    agent_registry=agent_registry,
    parser=parser,
    aggregator=aggregator,
    hold_extractor=hold_extractor,
    debug=env.debug,
    aggregate_round_to_us=learning_defaults["aggregate_round_to_us"],
    aggregate_min_match_ratio=learning_defaults["aggregate_min_match_ratio"],
    hold_idle_timeout_ms=learning_defaults["hold_idle_timeout_ms"],
    status_comm=status_comm,
)


def require_api_key(x_api_key: Optional[str]) -> None:
    if not env.api_key:
        return
    if not x_api_key or x_api_key != env.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def agent_error_response(error: AgentRoutingError) -> JSONResponse:
    payload = AgentErrorResponse(code=error.code, message=error.message)
    return JSONResponse(
        status_code=error.status_code,
        content=payload.model_dump(),
    )


def apply_hub_agent_setting(enabled: bool) -> None:
    if enabled:
        agent_registry.register_agent(local_agent)
    else:
        agent_registry.unregister_agent(local_agent.agent_id)


def resolve_hub_agent_setting() -> bool:
    settings = database.settings.get_ui_settings()
    hub_is_agent = bool(settings.get("hub_is_agent", True))
    if env.local_agent_enabled is None:
        return hub_is_agent
    if env.local_agent_enabled != hub_is_agent:
        database.settings.update_ui_settings(hub_is_agent=env.local_agent_enabled)
    return bool(env.local_agent_enabled)


def decorate_settings_payload(settings: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(settings or {})
    payload["settings_master_key_configured"] = settings_cipher.is_configured
    payload["mqtt_status"] = runtime_loader.status()
    return payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init()
    # Load persisted learning defaults after the settings table exists.
    learning.apply_learning_settings(database.settings.get_learning_settings())
    # Store the running loop so sync code can broadcast status updates.
    status_comm.attach_loop(asyncio.get_running_loop())

    apply_hub_agent_setting(resolve_hub_agent_setting())
    runtime_loader.start()
    pairing_manager.start()

    # Debug capture data can grow quickly; keep it only when DEBUG=true.
    if not env.debug:
        database.captures.clear()

    try:
        yield
    finally:
        pairing_manager.stop()
        runtime_loader.stop()
        learning.stop()


app = FastAPI(
    title="mqtt-ir-module",
    version=SOFTWARE_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.exception_handler(AgentRoutingError)
async def agent_routing_error_handler(request: Request, exc: AgentRoutingError) -> JSONResponse:
    return agent_error_response(exc)

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
    return {"ok": True}


@api.get("/status/electronics")
def status_electronics() -> Dict[str, Any]:
    return {
        "ir_device": env.ir_rx_device,
        "ir_rx_device": env.ir_rx_device,
        "ir_tx_device": env.ir_tx_device,
        "debug": env.debug,
    }


@api.get("/status/learning")
def status_learning() -> Dict[str, Any]:
    return {
        "learn_enabled": learning.is_learning,
        "learn_remote_id": learning.remote_id,
        "learn_remote_name": learning.remote_name,
    }


@api.get("/status/mqtt")
def status_mqtt() -> Dict[str, Any]:
    return runtime_loader.status()


@api.get("/status/pairing")
def status_pairing() -> Dict[str, Any]:
    return pairing_manager.status()


@api.get("/agents")
def list_agents() -> List[Dict[str, Any]]:
    return agent_registry.list_agents()


@api.get("/agents/{agent_id}")
def get_agent(agent_id: str) -> Dict[str, Any]:
    agent = agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Unknown agent_id")
    return agent


@api.put("/agents/{agent_id}")
def update_agent(
    agent_id: str,
    body: AgentUpdate,
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        changes = body.model_dump(exclude_unset=True)
        updated = agent_registry.update_agent(
            agent_id=agent_id,
            changes=changes,
        )
        return updated
    except ValueError as e:
        message = str(e)
        if message == "Unknown agent_id":
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=400, detail=message)


@api.post("/pairing/open")
def pairing_open(
    body: PairingOpenRequest,
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        duration = int(body.duration_seconds or pairing_manager.DEFAULT_WINDOW_SECONDS)
        return pairing_manager.open_pairing(duration_seconds=duration)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.post("/pairing/close")
def pairing_close(x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    try:
        return pairing_manager.close_pairing()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------
# Settings (UI)
# -----------------


@api.get("/settings")
def get_settings() -> Dict[str, Any]:
    return decorate_settings_payload(database.settings.get_ui_settings())


@api.put("/settings")
def update_settings(body: SettingsUpdate, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    require_api_key(x_api_key)
    if body.hub_is_agent is not None:
        raise HTTPException(
            status_code=400,
            detail="hub_is_agent is managed via LOCAL_AGENT_ENABLED and is read-only in settings.",
        )
    if (
        body.theme is None
        and body.language is None
        and body.homeassistant_enabled is None
        and body.mqtt_host is None
        and body.mqtt_port is None
        and body.mqtt_username is None
        and body.mqtt_password is None
        and body.mqtt_instance is None
        and body.press_takes_default is None
        and body.capture_timeout_ms_default is None
        and body.hold_idle_timeout_ms is None
        and body.aggregate_round_to_us is None
        and body.aggregate_min_match_ratio is None
    ):
        raise HTTPException(status_code=400, detail="at least one setting must be provided")
    try:
        mqtt_runtime_changed = any(
            value is not None
            for value in (
                body.homeassistant_enabled,
                body.mqtt_host,
                body.mqtt_port,
                body.mqtt_username,
                body.mqtt_password,
                body.mqtt_instance,
            )
        )
        updated = database.settings.update_ui_settings(
            theme=body.theme,
            language=body.language,
            homeassistant_enabled=body.homeassistant_enabled,
            mqtt_host=body.mqtt_host,
            mqtt_port=body.mqtt_port,
            mqtt_username=body.mqtt_username,
            mqtt_password=body.mqtt_password,
            mqtt_instance=body.mqtt_instance,
            settings_cipher=settings_cipher,
            press_takes_default=body.press_takes_default,
            capture_timeout_ms_default=body.capture_timeout_ms_default,
            hold_idle_timeout_ms=body.hold_idle_timeout_ms,
            aggregate_round_to_us=body.aggregate_round_to_us,
            aggregate_min_match_ratio=body.aggregate_min_match_ratio,
        )
        learning.apply_learning_settings(updated)
        if mqtt_runtime_changed:
            runtime_loader.reload()
            pairing_manager.stop()
            pairing_manager.start()
        return decorate_settings_payload(updated)
    except ValueError as e:
        message = str(e)
        if message == "settings_master_key_missing":
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "settings_master_key_missing",
                    "message": "SETTINGS_MASTER_KEY is required to store MQTT password.",
                },
            )
        if message == "mqtt_password_decrypt_failed":
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "mqtt_password_decrypt_failed",
                    "message": "Stored MQTT password cannot be decrypted with the current SETTINGS_MASTER_KEY.",
                },
            )
        raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        message = str(e)
        if "AES-GCM settings encryption" in message:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "settings_crypto_missing",
                    "message": "The cryptography package is required to encrypt MQTT passwords.",
                },
            )
        raise HTTPException(status_code=400, detail=message)


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
            assigned_agent_id=body.assigned_agent_id,
            carrier_hz=body.carrier_hz,
            duty_cycle=body.duty_cycle,
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


@api.post(
    "/learn/start",
    response_model=LearnStartResponse,
    responses={400: {"model": AgentErrorResponse}, 503: {"model": AgentErrorResponse}},
)
def learn_start(body: LearnStart, x_api_key: Optional[str] = Header(default=None)) -> LearnStartResponse:
    require_api_key(x_api_key)
    try:
        result = learning.start(remote_id=body.remote_id, extend=body.extend)
        return LearnStartResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api.post(
    "/learn/capture",
    response_model=LearnCaptureResponse,
    responses={400: {"model": AgentErrorResponse}, 503: {"model": AgentErrorResponse}},
)
def learn_capture(body: LearnCapture, x_api_key: Optional[str] = Header(default=None)) -> LearnCaptureResponse:
    require_api_key(x_api_key)

    learning_settings = database.settings.get_learning_settings()
    learning.apply_learning_settings(learning_settings)
    takes = body.takes if body.takes is not None else learning_settings["press_takes_default"]
    timeout_ms = body.timeout_ms if body.timeout_ms is not None else learning_settings["capture_timeout_ms_default"]

    try:
        result = learning.capture(
            remote_id=body.remote_id,
            mode=body.mode,
            takes=takes,
            timeout_ms=timeout_ms,
            overwrite=body.overwrite,
            button_name=body.button_name,
        )
        return LearnCaptureResponse.model_validate(result)
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


@api.post(
    "/send",
    response_model=SendResponse,
    responses={400: {"model": AgentErrorResponse}, 503: {"model": AgentErrorResponse}},
)
def send_ir(body: SendRequest, x_api_key: Optional[str] = Header(default=None)) -> SendResponse:
    require_api_key(x_api_key)

    if learning.is_learning:
        raise HTTPException(status_code=409, detail="Cannot send while learning is active")

    try:
        button = database.buttons.get(body.button_id)
        signals = database.signals.list_by_button(body.button_id)
        if not signals:
            raise ValueError("No signals for button")

        remote = database.remotes.get(int(button["remote_id"]))
        agent = agent_registry.resolve_agent_for_remote(remote_id=int(remote["id"]), remote=remote)

        payload = {
            "button_id": body.button_id,
            "mode": body.mode,
            "hold_ms": body.hold_ms,
            "press_initial": signals.get("press_initial"),
            "hold_initial": signals.get("hold_initial"),
            "hold_repeat": signals.get("hold_repeat"),
            "hold_gap_us": signals.get("hold_gap_us"),
            "carrier_hz": remote.get("carrier_hz"),
            "duty_cycle": remote.get("duty_cycle"),
        }

        result = agent.send(payload)
        agent_registry.mark_agent_activity(agent.agent_id)
        return SendResponse.model_validate(result)
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
