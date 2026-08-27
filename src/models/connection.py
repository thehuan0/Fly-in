from pydantic import BaseModel, Field
from .node import Node


class Connection(BaseModel):
    """Represents a bidirectional travel path between two Node objects."""

    node_a: Node
    node_b: Node
    max_link_capacity: int = Field(default=1, ge=1)

    @property
    def uid(self) -> frozenset[str]:
        """Returns a unique, order-independent identifier."""
        return frozenset([self.node_a.name, self.node_b.name])

    @property
    def name(self) -> str:
        """Returns the formatted connection name used in simulation logs."""
        names = sorted([self.node_a.name, self.node_b.name])
        return f"{names[0]}-{names[1]}"

    def get_destination(self, origin_name: str) -> Node:
        """Returns the Node at the opposite end of the given origin."""
        if self.node_a.name == origin_name:
            return self.node_b
        return self.node_a

    class Config:
        arbitrary_types_allowed = True