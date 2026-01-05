from typing import Literal, Optional
from pydantic import BaseModel, Field


Theme = Literal["system", "light", "dark"]


class SettingsUpdate(BaseModel):
    theme: Optional[Theme] = Field(default=None, description="UI theme")
    language: Optional[str] = Field(default=None, min_length=2, max_length=16, description="UI language code (e.g. en, de, pt-PT)")
    