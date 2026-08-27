from enum import Enum
from pydantic import BaseModel, Field


class NodeType(Enum):
    NORMAL = "normal"
    PRIORITY = "priority"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"


class Node(BaseModel):
    """Represents a distinct zone or waypoint within the simulation map."""

    name: str
    x: int
    y: int
    node_type: NodeType = Field(default=NodeType.NORMAL, alias="zone")
    max_drones: int = Field(default=1, ge=1)
    color: str = "none"

    @property
    def cost(self) -> int:
        """Returns the movement cost in turns."""
        return 2 if self.node_type == NodeType.RESTRICTED else 1

    class Config:
        populate_by_name = True
