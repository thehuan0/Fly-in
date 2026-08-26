from typing import List, Dict, Set, Tuple
from src.models.node import Node, NodeType
from src.models.drone import Drone


class SimulationEngine:
    """
    Handles turn progression, move validation, and status tracking.

    Translates the solver's strategic commands into concrete drone movements.
    Ensures drones occupying restricted multi-turn connections are processed
    correctly before logging the final standard output.
    """
    def __init__(self, drones: List[Drone], end_node: Node) -> None:
        self.drones = drones
        self.end_node = end_node
        self.turn = 0
        self.in_transit: Dict[int, Node] = {}
        self.delivered_ids: Set[int] = set()

    def run_turn(self, planned_moves: Dict[int, Node]) -> str:
        """
        Executes a simulation tick and returns the formatted movement log.

        Args:
            planned_moves (Dict[int, Node]):
            The target node for each active drone ID.

        Returns:
            str: Space-separated movement logs sorted numerically by drone ID.
        """
        self.turn += 1
        turn_logs_data: List[Tuple[int, str]] = []
        processed_this_turn: Set[int] = set()

        landing_ids = list(self.in_transit.keys())
        for d_id in landing_ids:
            target = self.in_transit.pop(d_id)
            drone = next(d for d in self.drones if d.id == d_id)
            drone.location = target

            turn_logs_data.append((drone.id, f"{drone.name}-{target.name}"))
            processed_this_turn.add(d_id)

            if target.name == self.end_node.name:
                self.delivered_ids.add(drone.id)

        for d_id, target in planned_moves.items():
            if d_id in self.delivered_ids or d_id in processed_this_turn:
                continue

            drone = next(d for d in self.drones if d.id == d_id)
            origin = drone.location

            if isinstance(origin, Node) and origin.name == target.name:
                continue

            if target.node_type == NodeType.RESTRICTED:
                conn_name = "-".join(sorted([origin.name, target.name]))
                self.in_transit[d_id] = target
                turn_logs_data.append(
                    (drone.id, f"{drone.name}-{conn_name}")
                )
            else:
                drone.location = target
                turn_logs_data.append(
                    (drone.id, f"{drone.name}-{target.name}")
                )
                if target.name == self.end_node.name:
                    self.delivered_ids.add(drone.id)

        occupancy: Dict[str, int] = {}
        for d in self.drones:
            if d.id in self.delivered_ids or d.id in self.in_transit:
                continue
            loc = d.location
            if (
                isinstance(loc, Node) and
                "start" not in loc.name.lower() and
                loc.name != self.end_node.name
            ):
                occupancy[loc.name] = occupancy.get(loc.name, 0) + 1
                if occupancy[loc.name] > loc.max_drones:
                    raise RuntimeError(
                        f"Engine Fault: {loc.name} capacity exceeded "
                        f"by Drone {d.id}"
                    )

        sorted_logs = [
            log_str for _, log_str in sorted(
                turn_logs_data, key=lambda item: item[0]
            )
        ]
        return " ".join(sorted_logs)

    @property
    def all_delivered(self) -> bool:
        """Returns True if every drone has reached the destination node."""
        return len(self.delivered_ids) == len(self.drones)
