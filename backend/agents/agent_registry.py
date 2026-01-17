import threading
import time
from typing import Dict, Any, List, Optional

from database import Database

from .agent import Agent
from .errors import AgentRoutingError


class AgentRegistry:
    def __init__(self, database: Database) -> None:
        self._db = database
        self._agents: Dict[str, Agent] = {}
        self._lock = threading.Lock()

    def register_agent(self, agent: Agent) -> None:
        with self._lock:
            self._agents[agent.agent_id] = agent
        status = agent.get_status()
        self._db.agents.upsert(
            agent_id=agent.agent_id,
            name=agent.name,
            transport=agent.transport,
            status=str(status.get("status") or "online"),
            capabilities=agent.capabilities,
            last_seen=time.time(),
        )

    def unregister_agent(self, agent_id: str) -> None:
        with self._lock:
            self._agents.pop(agent_id, None)
        self._db.agents.set_status(agent_id=agent_id, status="offline", last_seen=time.time())

    def list_agents(self) -> List[Dict[str, Any]]:
        agents = self._db.agents.list()
        active_ids = self._get_active_ids()
        for agent in agents:
            agent["is_active"] = agent.get("agent_id") in active_ids
        return agents

    def resolve_agent_for_remote(self, remote_id: int, remote: Optional[Dict[str, Any]] = None) -> Agent:
        remote = remote or self._db.remotes.get(remote_id)
        raw_assigned = remote.get("assigned_agent_id")
        assigned_agent_id = str(raw_assigned).strip() if raw_assigned is not None else ""
        assigned_agent_id = assigned_agent_id or None
        if assigned_agent_id:
            return self.get_agent_by_id(assigned_agent_id)

        active_ids = self._get_active_ids()
        if not active_ids:
            raise AgentRoutingError(code="no_agents", message="No agents are available", status_code=503)
        if len(active_ids) == 1:
            selected_id = next(iter(active_ids))
            self._db.remotes.set_assigned_agent(remote_id=remote_id, assigned_agent_id=selected_id)
            return self.get_agent_by_id(selected_id)

        raise AgentRoutingError(code="agent_required", message="Remote must be assigned to an agent", status_code=400)

    def get_agent_by_id(self, agent_id: str) -> Agent:
        if not agent_id:
            raise AgentRoutingError(code="agent_required", message="Remote must be assigned to an agent", status_code=400)
        with self._lock:
            agent = self._agents.get(agent_id)
        if not agent:
            raise AgentRoutingError(code="agent_offline", message="Assigned agent is offline or unavailable", status_code=503)
        self._db.agents.touch(agent_id=agent_id, last_seen=time.time())
        return agent

    def _get_active_ids(self) -> set[str]:
        with self._lock:
            return set(self._agents.keys())
