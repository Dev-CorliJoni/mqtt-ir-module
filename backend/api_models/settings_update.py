from typing import Literal, Optional
from pydantic import BaseModel, Field


Theme = Literal["system", "light", "dark"]


class SettingsUpdate(BaseModel):
    theme: Optional[Theme] = Field(default=None, description="UI theme")
    language: Optional[str] = Field(default=None, min_length=2, max_length=16, description="UI language code (e.g. en, de, pt-PT)")
    press_takes_default: Optional[int] = Field(default=None, ge=1, le=50, description="Default number of press takes")
    capture_timeout_ms_default: Optional[int] = Field(default=None, ge=100, le=60000, description="Default capture timeout in ms")
    hold_idle_timeout_ms: Optional[int] = Field(default=None, ge=50, le=2000, description="Hold idle timeout in ms")
    aggregate_round_to_us: Optional[int] = Field(default=None, ge=1, le=1000, description="Aggregation rounding step in microseconds")
    aggregate_min_match_ratio: Optional[float] = Field(default=None, ge=0.1, le=1.0, description="Aggregation minimum match ratio")
