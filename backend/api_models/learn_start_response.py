from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class LearnStartResponse(BaseModel):
    learn_enabled: bool = Field(..., description="Whether a learning session is active")
    remote_id: Optional[int] = Field(default=None, description="Remote id for the active session")
    remote_name: Optional[str] = Field(default=None, description="Remote name for the active session")
    agent_id: Optional[str] = Field(default=None, description="Agent id handling this session")
    extend: Optional[bool] = Field(default=None, description="Whether the session extends an existing remote")
    started_at: Optional[float] = Field(default=None, description="Session start timestamp")
    last_button_id: Optional[int] = Field(default=None, description="Last captured button id")
    last_button_name: Optional[str] = Field(default=None, description="Last captured button name")
    next_button_index: Optional[int] = Field(default=None, description="Next auto-generated button index")
    logs: Optional[List[Dict[str, Any]]] = Field(default=None, description="Learning session logs")
