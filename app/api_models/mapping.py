from pydantic import BaseModel


class MappingCreate(BaseModel):
    device_name: str
    action_name: str
    code_id: int
    