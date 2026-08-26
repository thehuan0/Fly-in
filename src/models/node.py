from pydantic import BaseModel, Field
from enum import Enum


class NodeType(Enum):
    NORMAL = "normal"
    PRIORITY = "priority"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"


class Node(BaseModel):
    """Represents a distinct zone or waypoint within the simulation map."""
    name: str
    x: int = Field(...)
    y: int = Field(...)

    node_type: NodeType = Field(default=NodeType.NORMAL, alias="zone")
    max_drones: int = Field(default=1, ge=1)
    color: str = "none"

    @property
    def cost(self) -> int:
        """Returns the movement cost in turns."""
        if self.node_type == NodeType.RESTRICTED:
            return 2
        return 1

    class Config:
        populate_by_name = True
