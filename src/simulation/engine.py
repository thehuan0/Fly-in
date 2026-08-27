from typing import List, Dict, Set, Tuple
from src.models.node import Node, NodeType
from src.models.drone import Drone


class SimulationEngine:
    """Handles turn progression, move validation, and status tracking."""

    def __init__(self, drones: List[Drone], end_node: Node) -> None:
        self.drones = drones
        self.end_node = end_node
        self.turn = 0
        self.in_transit: Dict[int, Node] = {}
        self.delivered_ids: Set[int] = set()

    def run_turn(self, planned_moves: Dict[int, Node]) -> str:
        """Executes a simulation tick and returns the formatted log."""
        self.turn += 1
        turn_logs_data: List[Tuple[int, str]] = []
        processed_this_turn: Set[int] = set()

        self._process_landings(turn_logs_data, processed_this_turn)
        self._process_departures(
            planned_moves, turn_logs_data, processed_this_turn
        )
        self._validate_capacities()

        sorted_logs = [
            log_str for _, log_str in sorted(
                turn_logs_data, key=lambda item: item[0]
            )
        ]
        return " ".join(sorted_logs)

    def _process_landings(
        self, logs: List[Tuple[int, str]], processed: Set[int]
    ) -> None:
        """Resolves drones arriving from a multi-turn restricted transit."""
        landing_ids = list(self.in_transit.keys())
        for d_id in landing_ids:
            target = self.in_transit.pop(d_id)
            drone = next(d for d in self.drones if d.id == d_id)
            drone.location = target

            logs.append((drone.id, f"{drone.name}-{target.name}"))
            processed.add(d_id)

            if target.name == self.end_node.name:
                self.delivered_ids.add(drone.id)

    def _process_departures(
        self,
        moves: Dict[int, Node],
        logs: List[Tuple[int, str]],
        processed: Set[int]
    ) -> None:
        """Processes drones initiating new movements."""
        for d_id, target in moves.items():
            if d_id in self.delivered_ids or d_id in processed:
                continue

            drone = next(d for d in self.drones if d.id == d_id)
            origin = drone.location

            if isinstance(origin, Node) and origin.name == target.name:
                continue

            if target.node_type == NodeType.RESTRICTED:
                conn_name = "-".join(sorted([origin.name, target.name]))
                self.in_transit[d_id] = target
                logs.append((drone.id, f"{drone.name}-{conn_name}"))
            else:
                drone.location = target
                logs.append((drone.id, f"{drone.name}-{target.name}"))
                if target.name == self.end_node.name:
                    self.delivered_ids.add(drone.id)

    def _validate_capacities(self) -> None:
        """Ensures zone limitations are strictly respected."""
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

    @property
    def all_delivered(self) -> bool:
        """Returns True if every drone has reached the destination node."""
        return len(self.delivered_ids) == len(self.drones)