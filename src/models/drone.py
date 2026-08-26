from pydantic import BaseModel, Field
from .node import Node


class Drone(BaseModel):
    """Represents a single drone entity within the simulation."""
    id: int = Field(..., ge=1)
    location: Node

    @property
    def name(self) -> str:
        return f"D{self.id}"

    class Config:
        arbitrary_types_allowed = True
