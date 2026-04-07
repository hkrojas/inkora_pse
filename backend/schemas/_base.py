"""schemas/_base.py — Base compartida."""
from pydantic import BaseModel, ConfigDict


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
