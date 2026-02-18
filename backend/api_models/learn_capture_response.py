from typing import Dict, Any

from pydantic import BaseModel, Field


class LearnCaptureResponse(BaseModel):
    remote_id: int = Field(..., description="Remote id that received a capture")
    button: Dict[str, Any] = Field(..., description="Button record associated with the capture")
    signals: Dict[str, Any] = Field(..., description="Signal payload stored for the button")
