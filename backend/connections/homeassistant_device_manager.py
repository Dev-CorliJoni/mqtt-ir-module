import json
import logging
import threading
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from jhomeassistant import HomeAssistantConnection, HomeAssistantOrigin
from jhomeassistant.homeassistant_device import HomeAssistantDevice
from jhomeassistant.entities.update_entity import UpdateEntity
from jhomeassistant.entities.event_entity import EventEntity
from jhomeassistant.entities.button_entity import ButtonEntity
from jhomeassistant.entities.select_entity import SelectEntity
from jmqtt import QualityOfService as QoS

from firmware.firmware_catalog import FirmwareCatalog
from runtime_version import SOFTWARE_VERSION


GITHUB_RELEASES_API = "https://api.github.com/repos/Dev-CorliJoni/mqtt-ir-module/releases/latest"
PROJECT_GITHUB_URL = "https://github.com/Dev-CorliJoni/mqtt-ir-module"
HUB_ORIGIN_NAME = "IR Hub"
UNASSIGNED_OPTION = "Unassigned"

_HUB_UPDATE_SCHEDULE_INTERVAL = 3600.0
_AGENT_OTA_SCHEDULE_INTERVAL = 300.0
_REPUBLISH_TIMEOUT = 5.0


class HomeAssistantDeviceManager:
    """Builds and maintains the HA discovery tree.

    Architecture:
      - Hub-Origin holds the Hub-Device + all unassigned Remote-Devices.
      - Per Agent: own Origin holding the Agent-Self-Device + assigned Remote-Devices.
      - Each Remote-Device has a SelectEntity to (re)assign the agent from HA.
      - Assigned Remote-Devices additionally have ButtonEntities (one per button).
    """

    def __init__(
        self,
        database,
        runtime_state_hub,
        firmware_catalog: FirmwareCatalog,
        ir_send_fn: Callable[[int, str], None],
        command_client,
        hub_public_url: str = "",
    ) -> None:
        self._database = database
        self._runtime_state_hub = runtime_state_hub
        self._firmware_catalog = firmware_catalog
        self._ir_send_fn = ir_send_fn
        self._command_client = command_client
        self._hub_public_url = str(hub_public_url or "").strip()
        self._runtime_loader = None

        self._lock = threading.RLock()
        self._logger = logging.getLogger("homeassistant_device_manager")

        self._ha_connection: Optional[HomeAssistantConnection] = None
        self._hub_origin: Optional[HomeAssistantOrigin] = None
        self._hub_device: Optional[HomeAssistantDevice] = None
        self._hub_update_entity: Optional[UpdateEntity] = None

        # agent_id -> Origin / Self-Device / OTA-UpdateEntity / Log-EventEntity
        self._agent_origins: Dict[str, HomeAssistantOrigin] = {}
        self._agent_self_devices: Dict[str, HomeAssistantDevice] = {}
        self._agent_update_entities: Dict[str, UpdateEntity] = {}
        self._agent_log_entities: Dict[str, EventEntity] = {}

        # remote_id -> Device
        self._remote_devices: Dict[int, HomeAssistantDevice] = {}

    # ------------------------------------------------------------------
    # Wiring (called from main.py after dependent objects are constructed)
    # ------------------------------------------------------------------

    def set_runtime_loader(self, runtime_loader) -> None:
        self._runtime_loader = runtime_loader

    def set_runtime_state_hub(self, runtime_state_hub) -> None:
        self._runtime_state_hub = runtime_state_hub

    def set_command_client(self, command_client) -> None:
        self._command_client = command_client

    # ------------------------------------------------------------------
    # Public lifecycle API
    # ------------------------------------------------------------------

    def setup(self, ha_connection: HomeAssistantConnection, origin_name: str = HUB_ORIGIN_NAME) -> None:
        """Called by HomeAssistantHandler before ha_connection.run().
        Builds the full HA tree from current DB + runtime state.
        """
        with self._lock:
            self._ha_connection = ha_connection
            self._hub_origin = None
            self._hub_device = None
            self._hub_update_entity = None
            self._agent_origins.clear()
            self._agent_self_devices.clear()
            self._agent_update_entities.clear()
            self._agent_log_entities.clear()
            self._remote_devices.clear()

            node_id = self._resolve_node_id()

            # Hub-Origin (always exists)
            hub_origin = HomeAssistantOrigin(
                name=origin_name,
                sw_version=SOFTWARE_VERSION,
                url=self._origin_url_for_hub(),
            )
            hub_device = self._build_hub_device(node_id)
            hub_origin.add_devices(hub_device)
            self._hub_origin = hub_origin
            self._hub_device = hub_device

            # Agent-Origins
            agents = [a for a in self._database.agents.list() if not bool(a.get("pending"))]
            for agent_data in agents:
                transport = str(agent_data.get("transport") or "").strip()
                if transport not in ("mqtt", "local"):
                    continue
                agent_id = str(agent_data.get("agent_id") or "").strip()
                if not agent_id:
                    continue
                self._build_agent_origin(agent_id, agent_data, node_id)

            # Remote-Devices (assigned → agent-origin, unassigned → hub-origin)
            for remote in self._database.remotes.list():
                self._build_remote_device(remote, node_id)

            # Add all origins to the connection
            origins: List[HomeAssistantOrigin] = [hub_origin] + list(self._agent_origins.values())

        ha_connection.add_origin(*origins)
        self._subscribe_all_agent_logs(ha_connection)

    # ------------------------------------------------------------------
    # Agent mutations (called from main.py / runtime hub hooks)
    # ------------------------------------------------------------------

    def add_agent(self, agent_id: str) -> None:
        normalized_id = str(agent_id or "").strip()
        if not normalized_id:
            return

        with self._lock:
            ha_connection = self._ha_connection
            if ha_connection is None:
                return
            if normalized_id in self._agent_origins:
                return
            agent_data = self._database.agents.get(normalized_id)
            if not agent_data or bool(agent_data.get("pending")):
                return

            node_id = self._resolve_node_id()
            origin = self._build_agent_origin(normalized_id, agent_data, node_id)
            if origin is None:
                return

        # Add origin (must be outside lock since add_origin walks _origins internally)
        ha_connection.add_origin(origin)

        # Activate entities for the new self-device
        with self._lock:
            self_device = self._agent_self_devices.get(normalized_id)
        if self_device is not None:
            self._activate_device_entities(ha_connection, self_device)

        self._subscribe_agent_logs(ha_connection, normalized_id)
        self._refresh_select_options_for_all_remotes(ha_connection)

        self._republish(ha_connection)

    def remove_agent(self, agent_id: str) -> None:
        normalized_id = str(agent_id or "").strip()
        if not normalized_id:
            return

        with self._lock:
            ha_connection = self._ha_connection
            if ha_connection is None:
                return
            origin = self._agent_origins.pop(normalized_id, None)
            self_device = self._agent_self_devices.pop(normalized_id, None)
            self._agent_update_entities.pop(normalized_id, None)
            self._agent_log_entities.pop(normalized_id, None)

            # Move all remote-devices that were under this agent's origin to the hub-origin
            # (they might persist in DB with assigned_agent_id intact, or be deassigned by the
            # caller — either way we let update_remote rebuild them after this call).
            remote_ids_under_agent: List[int] = []
            if origin is not None:
                for device in list(origin._devices):
                    for rid, dev in list(self._remote_devices.items()):
                        if dev is device and dev is not self_device:
                            remote_ids_under_agent.append(rid)

        if origin is not None:
            try:
                ha_connection.remove_origin(origin, publish_timeout=_REPUBLISH_TIMEOUT)
            except Exception as exc:
                self._logger.warning(f"remove_origin failed for agent {normalized_id}: {exc}")

        # Remote-Devices that were attached to the removed origin are gone from HA now.
        # Re-add them under the appropriate origin (hub or different agent if reassigned).
        for rid in remote_ids_under_agent:
            with self._lock:
                self._remote_devices.pop(rid, None)
            try:
                self.add_remote(rid)
            except Exception as exc:
                self._logger.warning(f"re-add remote {rid} after agent removal failed: {exc}")

        self._refresh_select_options_for_all_remotes(ha_connection)
        self._republish(ha_connection)

    def update_agent(self, agent_id: str) -> None:
        """Rename, sw_version change, or other agent metadata change."""
        normalized_id = str(agent_id or "").strip()
        if not normalized_id:
            return

        with self._lock:
            ha_connection = self._ha_connection
            if ha_connection is None:
                return
            agent_data = self._database.agents.get(normalized_id)
            if not agent_data or bool(agent_data.get("pending")):
                return

            origin = self._agent_origins.get(normalized_id)
            self_device = self._agent_self_devices.get(normalized_id)
            if origin is None or self_device is None:
                # Agent didn't have an origin yet — treat as add.
                self.add_agent(normalized_id)
                return

            new_name = str(agent_data.get("name") or normalized_id).strip()
            runtime_state = self._runtime_state_hub.get_state(normalized_id) or {}
            new_sw_version = str(runtime_state.get("sw_version") or agent_data.get("sw_version") or "").strip()

            origin.name = new_name
            if new_sw_version:
                origin.sw_version = new_sw_version
                self_device.sw_version = new_sw_version
            self_device.name = new_name
            self_device.configuration_url = self._device_url_for_agent(normalized_id) or None
            origin.url = self._origin_url_for_agent(normalized_id) or None

        self._refresh_select_options_for_all_remotes(ha_connection)
        self._republish(ha_connection)

    # ------------------------------------------------------------------
    # Remote mutations
    # ------------------------------------------------------------------

    def add_remote(self, remote_id: int) -> None:
        rid = int(remote_id)
        with self._lock:
            ha_connection = self._ha_connection
            if ha_connection is None:
                return
            if rid in self._remote_devices:
                return
            try:
                remote = self._database.remotes.get(rid)
            except Exception:
                return
            node_id = self._resolve_node_id()
            self._build_remote_device(remote, node_id)
            device = self._remote_devices.get(rid)

        if device is not None:
            self._activate_device_entities(ha_connection, device)
        self._republish(ha_connection)

    def update_remote(self, remote_id: int) -> None:
        """Handle rename, reassignment or button changes for a remote."""
        rid = int(remote_id)
        with self._lock:
            ha_connection = self._ha_connection
            if ha_connection is None:
                return
            old_device = self._remote_devices.pop(rid, None)

        if old_device is not None:
            try:
                ha_connection.remove_device(old_device, publish_timeout=_REPUBLISH_TIMEOUT)
            except Exception as exc:
                self._logger.warning(f"remove_device failed for remote {rid}: {exc}")

        self.add_remote(rid)

    def remove_remote(self, remote_id: int) -> None:
        rid = int(remote_id)
        with self._lock:
            ha_connection = self._ha_connection
            if ha_connection is None:
                return
            device = self._remote_devices.pop(rid, None)
        if device is None:
            return
        try:
            ha_connection.remove_device(device, publish_timeout=_REPUBLISH_TIMEOUT)
        except Exception as exc:
            self._logger.warning(f"remove_device failed for remote {rid}: {exc}")

    # ------------------------------------------------------------------
    # Settings change
    # ------------------------------------------------------------------

    def update_hub_public_url(self, url: str) -> None:
        new_url = str(url or "").strip()
        with self._lock:
            if new_url == self._hub_public_url:
                return
            self._hub_public_url = new_url
            ha_connection = self._ha_connection

            # Update existing devices/origins with the new URL
            if self._hub_origin is not None:
                self._hub_origin.url = self._origin_url_for_hub() or None
            if self._hub_device is not None:
                self._hub_device.configuration_url = self._origin_url_for_hub() or None
            for agent_id, origin in self._agent_origins.items():
                origin.url = self._origin_url_for_agent(agent_id) or None
            for agent_id, device in self._agent_self_devices.items():
                device.configuration_url = self._device_url_for_agent(agent_id) or None
            for rid, device in self._remote_devices.items():
                device.configuration_url = self._device_url_for_remote(rid) or None

        if ha_connection is not None:
            self._republish(ha_connection)

    # ------------------------------------------------------------------
    # Hub origin / device
    # ------------------------------------------------------------------

    def _build_hub_device(self, node_id: str) -> HomeAssistantDevice:
        device = HomeAssistantDevice(name=HUB_ORIGIN_NAME, identifier=f"hub-{node_id}")
        device.manufacturer = "mqtt-ir-module"
        device.sw_version = SOFTWARE_VERSION
        url = self._origin_url_for_hub()
        if url:
            device.configuration_url = url

        update_entity = UpdateEntity(
            name="Hub Software Update",
            state_topic=f"ir/hubs/{node_id}/ha/hub/update/state",
        )

        def _check_hub_update(connection) -> None:
            latest = self._fetch_github_latest_version()
            try:
                update_entity.publish(
                    installed_version=SOFTWARE_VERSION,
                    latest_version=latest or SOFTWARE_VERSION,
                )
            except Exception as exc:
                self._logger.debug(f"Hub update publish failed: {exc}")

        update_entity.add_schedule(_HUB_UPDATE_SCHEDULE_INTERVAL, _check_hub_update)
        device.add_entities(update_entity)
        self._hub_update_entity = update_entity
        return device

    def _fetch_github_latest_version(self) -> str:
        try:
            req = urllib.request.Request(
                GITHUB_RELEASES_API,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "mqtt-ir-module"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            tag = str(data.get("tag_name") or "").strip().lstrip("v")
            return tag
        except Exception as exc:
            self._logger.debug(f"GitHub version check failed: {exc}")
            return ""

    # ------------------------------------------------------------------
    # Agent origin / self-device
    # ------------------------------------------------------------------

    def _build_agent_origin(
        self,
        agent_id: str,
        agent_data: Dict[str, Any],
        node_id: str,
    ) -> Optional[HomeAssistantOrigin]:
        if agent_id in self._agent_origins:
            return self._agent_origins[agent_id]

        name = str(agent_data.get("name") or agent_id).strip()
        runtime_state = self._runtime_state_hub.get_state(agent_id) or {} if self._runtime_state_hub else {}
        sw_version = str(runtime_state.get("sw_version") or agent_data.get("sw_version") or "").strip()
        transport = str(agent_data.get("transport") or "").strip()

        origin = HomeAssistantOrigin(
            name=name,
            sw_version=sw_version or SOFTWARE_VERSION,
            url=self._origin_url_for_agent(agent_id) or None,
        )

        # Agent LWT only for MQTT-transported agents (local agent shares the hub LWT).
        if transport == "mqtt":
            lwt_topic = f"ir/agents/{agent_id}/state/availability"
            origin.availability.add(lwt_topic, payload_available="online", payload_not_available="offline")

        self_device = self._build_agent_self_device(agent_id, agent_data, node_id)
        origin.add_devices(self_device)

        self._agent_origins[agent_id] = origin
        self._agent_self_devices[agent_id] = self_device
        return origin

    def _build_agent_self_device(
        self,
        agent_id: str,
        agent_data: Dict[str, Any],
        node_id: str,
    ) -> HomeAssistantDevice:
        name = str(agent_data.get("name") or agent_id).strip()
        runtime_state = self._runtime_state_hub.get_state(agent_id) or {} if self._runtime_state_hub else {}
        ota_supported = bool(runtime_state.get("ota_supported"))
        sw_version = str(runtime_state.get("sw_version") or agent_data.get("sw_version") or "").strip()

        device = HomeAssistantDevice(name=name, identifier=agent_id)
        device.manufacturer = "mqtt-ir-module"
        if sw_version:
            device.sw_version = sw_version
        url = self._device_url_for_agent(agent_id)
        if url:
            device.configuration_url = url

        base = f"ir/hubs/{node_id}/ha/agents/{agent_id}"
        update_state_topic = f"{base}/update/state"
        update_command_topic = f"{base}/update/set" if ota_supported else None

        on_install = None
        if ota_supported:
            def on_install(connection, message, _aid=agent_id):
                self._handle_agent_ota_install(_aid)

        update_entity = UpdateEntity(
            name="Firmware Update",
            state_topic=update_state_topic,
            command_topic=update_command_topic,
            on_install=on_install,
        )

        def _refresh_ota(connection, _aid=agent_id, _ent=update_entity) -> None:
            self._publish_agent_update_state(_aid, _ent)

        update_entity.add_schedule(_AGENT_OTA_SCHEDULE_INTERVAL, _refresh_ota)

        log_entity = EventEntity(
            name="Agent Log",
            state_topic=f"{base}/logs/state",
            event_types=["info", "warn", "warning", "error"],
        )

        device.add_entities(update_entity, log_entity)

        self._agent_update_entities[agent_id] = update_entity
        self._agent_log_entities[agent_id] = log_entity
        return device

    def _publish_agent_update_state(self, agent_id: str, update_entity: UpdateEntity) -> None:
        if self._runtime_state_hub is None:
            return
        runtime_state = self._runtime_state_hub.get_state(agent_id) or {}
        ota_supported = bool(runtime_state.get("ota_supported"))
        agent_type = str(runtime_state.get("agent_type") or "").strip().lower()
        sw_version = str(runtime_state.get("sw_version") or "").strip()
        if not agent_type or not sw_version:
            return
        try:
            ota = self._firmware_catalog.ota_status(
                agent_type=agent_type,
                current_version=sw_version,
                ota_supported=ota_supported,
            )
            latest = str(ota.get("latest_version") or sw_version)
            update_entity.publish(installed_version=sw_version, latest_version=latest)
        except Exception as exc:
            self._logger.debug(f"Agent update state publish failed for {agent_id}: {exc}")

    def _handle_agent_ota_install(self, agent_id: str) -> None:
        self._logger.info(f"HA OTA install requested for agent {agent_id}")
        if not self._hub_public_url:
            self._logger.warning("OTA from HA skipped: hub_public_url not configured")
            return
        if self._command_client is None or self._runtime_state_hub is None:
            return

        runtime_state = self._runtime_state_hub.get_state(agent_id) or {}
        agent_type = str(runtime_state.get("agent_type") or "esp32").strip().lower()

        try:
            firmware = self._firmware_catalog.resolve_firmware(
                agent_type=agent_type,
                require_installable=True,
            )
        except ValueError as exc:
            self._logger.warning(f"OTA firmware not found for agent {agent_id}: {exc}")
            return

        ota_file = str(firmware.get("ota_file") or "").strip()
        if not ota_file:
            self._logger.warning(f"OTA firmware file missing for agent {agent_id}")
            return

        base = self._hub_public_url.rstrip("/")
        ota_url = f"{base}/firmware/files/{ota_file}"
        payload = {
            "version": str(firmware.get("version") or ""),
            "url": ota_url,
            "sha256": str(firmware.get("ota_sha256") or ""),
        }

        try:
            self._command_client.runtime_reboot(agent_id=agent_id)
        except Exception as exc:
            self._logger.warning(f"OTA pre-reboot failed for agent {agent_id}: {exc}")
            return

        agent_data_before = self._database.agents.get(agent_id)
        last_seen_before = float((agent_data_before or {}).get("last_seen") or 0)
        deadline = time.time() + 45
        came_back = False
        while time.time() < deadline:
            time.sleep(1)
            current = self._database.agents.get(agent_id)
            if (
                current
                and str(current.get("status") or "").strip().lower() == "online"
                and float(current.get("last_seen") or 0) > last_seen_before
            ):
                came_back = True
                break

        if not came_back:
            self._logger.warning(f"OTA from HA: agent {agent_id} did not come back after reboot")
            return

        try:
            self._command_client.runtime_ota_start(agent_id=agent_id, payload=payload)
        except Exception as exc:
            self._logger.warning(f"OTA start command failed for agent {agent_id}: {exc}")

    # ------------------------------------------------------------------
    # Remote device (under hub-origin if unassigned, agent-origin if assigned)
    # ------------------------------------------------------------------

    def _build_remote_device(
        self,
        remote: Dict[str, Any],
        node_id: str,
    ) -> Optional[HomeAssistantDevice]:
        remote_id = remote.get("id")
        remote_name = str(remote.get("name") or "").strip()
        if remote_id is None or not remote_name:
            return None
        rid = int(remote_id)

        assigned_agent_id = str(remote.get("assigned_agent_id") or "").strip() or None
        # Only treat as assigned if the agent actually has an origin
        target_origin: Optional[HomeAssistantOrigin] = None
        if assigned_agent_id and assigned_agent_id in self._agent_origins:
            target_origin = self._agent_origins[assigned_agent_id]
        else:
            target_origin = self._hub_origin

        if target_origin is None:
            return None

        device = HomeAssistantDevice(name=remote_name, identifier=f"remote-{rid}")
        device.manufacturer = "mqtt-ir-module"
        url = self._device_url_for_remote(rid)
        if url:
            device.configuration_url = url

        # SelectEntity (always present) — for assign/reassign from HA
        select_entity = self._build_select_entity(rid, assigned_agent_id, node_id)
        device.add_entities(select_entity)

        # Buttons only when assigned to an agent that has an origin
        if assigned_agent_id and target_origin is not self._hub_origin:
            try:
                buttons = self._database.buttons.list(remote_id=rid)
            except Exception:
                buttons = []
            for button in buttons:
                bid = button.get("id")
                bname = str(button.get("name") or "").strip()
                if bid is None or not bname:
                    continue
                press_topic = f"ir/hubs/{node_id}/ha/buttons/{int(bid)}/press"

                def _make_on_press(_bid: int = int(bid)):
                    def on_press(connection, message):
                        try:
                            self._ir_send_fn(_bid, "press")
                        except Exception as exc:
                            self._logger.warning(f"HA button press failed for button_id={_bid}: {exc}")
                    return on_press

                device.add_entities(ButtonEntity(
                    name=bname,
                    command_topic=press_topic,
                    on_press=_make_on_press(),
                ))

        target_origin.add_devices(device)
        self._remote_devices[rid] = device
        return device

    def _build_select_entity(self, remote_id: int, current_agent_id: Optional[str], node_id: str) -> SelectEntity:
        options, current_value = self._compute_select_options(current_agent_id)
        state_topic = f"ir/hubs/{node_id}/ha/remotes/{remote_id}/agent/state"
        command_topic = f"ir/hubs/{node_id}/ha/remotes/{remote_id}/agent/set"

        select_entity = SelectEntity(
            name="Assigned Agent",
            state_topic=state_topic,
            command_topic=command_topic,
            options=options,
            on_select=lambda conn, msg, _rid=remote_id: self._on_remote_assignment_change(_rid, msg),
            retain=True,
        )

        # Publish the current state once the entity is mqtt_connected. Schedule a one-shot
        # using the entity's schedule mechanism: a simple helper that publishes and self-removes.
        def _initial_publish(connection, _ent=select_entity, _val=current_value) -> None:
            try:
                _ent.publish(_val)
            except Exception as exc:
                self._logger.debug(f"SelectEntity initial publish failed for remote {remote_id}: {exc}")

        # Re-publish state every minute so HA stays in sync if it loses retained state.
        select_entity.add_schedule(60.0, _initial_publish)
        return select_entity

    def _compute_select_options(self, current_agent_id: Optional[str]) -> tuple[List[str], str]:
        """Build the option list shown in HA. Options use agent.name (User-Verantwortung
        for uniqueness — see Frage B). Returns (options, current_value).
        """
        names: List[str] = []
        try:
            for agent_data in self._database.agents.list():
                if bool(agent_data.get("pending")):
                    continue
                aname = str(agent_data.get("name") or agent_data.get("agent_id") or "").strip()
                if aname and aname not in names and aname != UNASSIGNED_OPTION:
                    names.append(aname)
        except Exception as exc:
            self._logger.debug(f"agents.list failed when building select options: {exc}")

        options = [UNASSIGNED_OPTION] + names

        current_value = UNASSIGNED_OPTION
        if current_agent_id:
            try:
                agent = self._database.agents.get(current_agent_id)
                if agent:
                    candidate = str(agent.get("name") or "").strip()
                    if candidate in options:
                        current_value = candidate
            except Exception:
                pass
        return options, current_value

    def _on_remote_assignment_change(self, remote_id: int, message) -> None:
        try:
            text = ""
            if hasattr(message, "text") and message.text is not None:
                text = str(message.text).strip()
        except Exception:
            text = ""

        if not text:
            return

        new_agent_id: Optional[str] = None
        if text != UNASSIGNED_OPTION:
            # Lookup agent by name
            try:
                for agent_data in self._database.agents.list():
                    if bool(agent_data.get("pending")):
                        continue
                    if str(agent_data.get("name") or "").strip() == text:
                        new_agent_id = str(agent_data.get("agent_id") or "").strip() or None
                        break
            except Exception as exc:
                self._logger.warning(f"agents.list failed during HA reassignment: {exc}")
                return
            if new_agent_id is None:
                self._logger.warning(f"HA reassign: agent name {text!r} not found")
                return

        try:
            current = self._database.remotes.get(remote_id)
        except Exception as exc:
            self._logger.warning(f"HA reassign: remote {remote_id} not found: {exc}")
            return

        try:
            self._database.remotes.update(
                remote_id=remote_id,
                name=current["name"],
                icon=current.get("icon"),
                assigned_agent_id=new_agent_id,
                carrier_hz=current.get("carrier_hz"),
                duty_cycle=current.get("duty_cycle"),
            )
        except Exception as exc:
            self._logger.warning(f"HA reassign: update failed for remote {remote_id}: {exc}")
            return

        self.update_remote(remote_id)

    def _refresh_select_options_for_all_remotes(self, ha_connection: HomeAssistantConnection) -> None:
        """Rebuild every remote's SelectEntity so the option list reflects the current agent pool."""
        with self._lock:
            remote_ids = list(self._remote_devices.keys())
        for rid in remote_ids:
            try:
                self.update_remote(rid)
            except Exception as exc:
                self._logger.debug(f"refresh_select for remote {rid} failed: {exc}")

    # ------------------------------------------------------------------
    # Log bridging
    # ------------------------------------------------------------------

    def _subscribe_all_agent_logs(self, ha_connection: HomeAssistantConnection) -> None:
        mqtt_connection = self._get_mqtt_connection(ha_connection)
        if mqtt_connection is None:
            return
        with self._lock:
            agent_ids = list(self._agent_log_entities.keys())
        for agent_id in agent_ids:
            self._do_subscribe_agent_logs(mqtt_connection, agent_id)

    def _subscribe_agent_logs(self, ha_connection: HomeAssistantConnection, agent_id: str) -> None:
        mqtt_connection = self._get_mqtt_connection(ha_connection)
        if mqtt_connection is None:
            return
        self._do_subscribe_agent_logs(mqtt_connection, agent_id)

    def _do_subscribe_agent_logs(self, mqtt_connection, agent_id: str) -> None:
        topic = f"ir/agents/{agent_id}/logs"
        try:
            mqtt_connection.subscribe(
                topic,
                lambda conn, client, userdata, msg, _aid=agent_id: self._on_agent_log(msg, _aid),
                qos=QoS.AtLeastOnce,
            )
        except Exception as exc:
            self._logger.warning(f"Failed to subscribe agent log topic {topic}: {exc}")

    def _on_agent_log(self, message, agent_id: str) -> None:
        with self._lock:
            entity = self._agent_log_entities.get(agent_id)
        if entity is None:
            return
        try:
            payload: Dict[str, Any] = {}
            if hasattr(message, "json_value") and isinstance(message.json_value, dict):
                payload = message.json_value
            elif hasattr(message, "text") and message.text:
                payload = json.loads(message.text)
            level = str(payload.get("level") or "info").strip().lower()
            if level not in ("info", "warn", "warning", "error"):
                level = "info"
            msg_text = str(payload.get("message") or "").strip()[:300]
            entity.publish(event_type=level, message=msg_text)
        except Exception as exc:
            self._logger.debug(f"Log bridge publish failed for {agent_id}: {exc}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_node_id(self) -> str:
        if self._runtime_loader is None:
            return "main"
        try:
            model = self._runtime_loader._mqtt_handler._active_model
            if model is not None:
                return str(model.node_id or "main")
        except Exception:
            pass
        return "main"

    def _get_mqtt_connection(self, ha_connection: HomeAssistantConnection):
        try:
            return ha_connection.get_connection()
        except Exception:
            return None

    def _origin_url_for_hub(self) -> str:
        return self._hub_public_url

    def _origin_url_for_agent(self, agent_id: str) -> str:
        if not self._hub_public_url:
            return ""
        return f"{self._hub_public_url.rstrip('/')}/agent/{agent_id}"

    def _device_url_for_agent(self, agent_id: str) -> str:
        return self._origin_url_for_agent(agent_id)

    def _device_url_for_remote(self, remote_id: int) -> str:
        if not self._hub_public_url:
            return ""
        return f"{self._hub_public_url.rstrip('/')}/remotes/{int(remote_id)}"

    def _activate_device_entities(self, ha_connection: HomeAssistantConnection, device: HomeAssistantDevice) -> None:
        for entity in list(device.entities):
            try:
                entity.mqtt_connected(ha_connection.get_connection)
            except Exception as exc:
                self._logger.debug(f"mqtt_connected failed for entity in device {device.name}: {exc}")

    def _republish(self, ha_connection: HomeAssistantConnection) -> None:
        try:
            ha_connection.republish_discovery(publish_timeout=_REPUBLISH_TIMEOUT)
        except Exception as exc:
            self._logger.warning(f"republish_discovery failed: {exc}")
