from pydantic import BaseModel


class Code(BaseModel):
    action_name: str
    