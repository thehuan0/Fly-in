from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class NodeType(Enum):
    NORMAL = "normal"
    PRIORITY = "priority"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"


class Node(BaseModel):
    name: str 
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    type: NodeType = NodeType.NORMAL 
    max_drones: int = Field(default=1, ge=1)
    color: Optional[str] = "none"

    @property
    def cost(self) -> int:
        """Returns the movement cost in turns."""
        if self.type == NodeType.RESTRICTED:
            return 2
        return 1

    class Config:
        populate_by_name = True
