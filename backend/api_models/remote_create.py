from pydantic import BaseModel, Field


class RemoteCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Human readable remote name")
