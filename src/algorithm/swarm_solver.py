import heapq
import itertools
import random
from typing import List, Dict, Tuple
from src.models.node import Node, NodeType
from src.models.connection import Connection
from src.models.drone import Drone


class SwarmSolver:
    """Time-Space A* Swarm Solver with strict reservation tracking."""

    def __init__(
        self, nodes: Dict[str, Node], connections: List[Connection]
    ) -> None:
        self.nodes = nodes
        self.connections = connections
        self.adj = self._build_adjacency()

        self.node_reservations: Dict[Tuple[str, int], int] = {}
        self.link_reservations: Dict[Tuple[str, int], int] = {}
        self.master_plan: Dict[int, List[Node]] = {}
        self.has_planned = False

    def _build_adjacency(self) -> Dict[str, List[Tuple[Node, Connection]]]:
        """Builds a fast-lookup graph adjacency list."""
        adj: Dict[str, List[Tuple[Node, Connection]]] = {
            name: [] for name in self.nodes
        }
        for conn in self.connections:
            adj[conn.node_a.name].append((conn.node_b, conn))
            adj[conn.node_b.name].append((conn.node_a, conn))
        return adj

    def _get_conn_name(self, name_a: str, name_b: str) -> str:
        """Standardizes connection naming."""
        names = sorted([name_a, name_b])
        return f"{names[0]}-{names[1]}"

    def _is_reachable(self, start_node: Node, end_node: Node) -> bool:
        """Validates if a physical path exists before planning."""
        visited = set()
        queue = [start_node.name]
        while queue:
            curr = queue.pop(0)
            if curr == end_node.name:
                return True
            if curr not in visited:
                visited.add(curr)
                for neighbor, _ in self.adj[curr]:
                    if neighbor.node_type != NodeType.BLOCKED:
                        queue.append(neighbor.name)
        return False

    def _precompute_heuristics(self, end_node: Node) -> Dict[str, int]:
        """Calculates exact unweighted BFS distances to the end node."""
        distances = {end_node.name: 0}
        queue = [end_node.name]

        while queue:
            curr = queue.pop(0)
            curr_dist = distances[curr]
            for neighbor, _ in self.adj[curr]:
                if neighbor.node_type != NodeType.BLOCKED:
                    if neighbor.name not in distances:
                        distances[neighbor.name] = curr_dist + neighbor.cost
                        queue.append(neighbor.name)
        return distances

    def _plan_all_flights(self, drones: List[Drone], end_node: Node) -> None:
        """Executes cooperative pathfinding for the entire swarm."""
        if not self._is_reachable(drones[0].location, end_node):
            raise ValueError(
                "Error: Destination zone is mathematically unreachable."
            )

        heuristics = self._precompute_heuristics(end_node)
        best_plan: Dict[int, List[Node]] = {}
        best_turns = 999999
        max_iterations = 100

        for seed in range(max_iterations):
            self.node_reservations = {}
            self.link_reservations = {}
            current_master_plan = {}
            random.seed(seed)

            drone_ids = [d.id for d in drones]
            random.shuffle(drone_ids)
            max_turn = 0
            valid = True

            for d_id in drone_ids:
                drone = next(d for d in drones if d.id == d_id)
                path = self._find_time_space_path(
                    drone.location, end_node, 0, heuristics
                )

                if not path:
                    valid = False
                    break

                current_master_plan[d_id] = path
                current_node = drone.location

                for idx, target in enumerate(path):
                    turn = idx + 1
                    if target.name == current_node.name:
                        # Wait in place OR 2nd turn of restricted node transit
                        res_key = (current_node.name, turn)
                        self.node_reservations[res_key] = (
                            self.node_reservations.get(res_key, 0) + 1
                        )
                    else:
                        conn_name = self._get_conn_name(
                            current_node.name, target.name
                        )
                        c_key = (conn_name, turn)
                        self.link_reservations[c_key] = (
                            self.link_reservations.get(c_key, 0) + 1
                        )

                        # Only reserve node arrival space if transit is done
                        if target.node_type != NodeType.RESTRICTED:
                            res_key = (target.name, turn)
                            self.node_reservations[res_key] = (
                                self.node_reservations.get(res_key, 0) + 1
                            )

                        current_node = target

                max_turn = max(max_turn, len(path))

            if valid and max_turn < best_turns:
                best_turns = max_turn
                best_plan = current_master_plan

        self.master_plan = best_plan
        self.has_planned = True

    def _find_time_space_path(
        self,
        start: Node,
        end: Node,
        start_turn: int,
        heuristics: Dict[str, int]
    ) -> List[Node]:
        """A* search through the time-expanded graph."""
        counter = itertools.count()
        start_h = heuristics.get(start.name, 9999)

        # (f_score, neg_prio, turns_taken, curr_turn, id, curr_name, path)
        pq: List[Tuple[int, int, int, int, int, str, List[Node]]] = [
            (start_h, 0, 0, start_turn, next(counter), start.name, [])
        ]
        visited = set()

        while pq:
            (f_score, neg_prio, turns_taken, curr_turn, _,
             curr_name, path) = heapq.heappop(pq)
            state = (curr_name, curr_turn)

            if state in visited:
                continue
            visited.add(state)

            if curr_name == end.name:
                return path

            current_node_obj = self.nodes[curr_name]
            node_cap = self.node_reservations.get(
                (curr_name, curr_turn + 1), 0
            )

            # Action 1: Wait in place
            if (
                curr_name == start.name or
                node_cap < current_node_obj.max_drones
            ):
                h_score = heuristics.get(curr_name, 9999)
                heapq.heappush(pq, (
                    turns_taken + 1 + h_score, neg_prio, turns_taken + 1,
                    curr_turn + 1, next(counter), curr_name,
                    path + [current_node_obj]
                ))

            # Action 2: Move to connected neighbors
            for neighbor, conn in self.adj[curr_name]:
                if neighbor.node_type == NodeType.BLOCKED:
                    continue

                arrival_turn = curr_turn + neighbor.cost
                next_node_cap = self.node_reservations.get(
                    (neighbor.name, arrival_turn), 0
                )

                has_room = (
                    neighbor.name == end.name or
                    next_node_cap < neighbor.max_drones
                )

                link_ok = True
                for t_offset in range(1, neighbor.cost + 1):
                    res_val = self.link_reservations.get(
                        (conn.name, curr_turn + t_offset), 0
                    )
                    if res_val >= conn.max_link_capacity:
                        link_ok = False
                        break

                if has_room and link_ok:
                    new_prio = neg_prio
                    if neighbor.node_type == NodeType.PRIORITY:
                        new_prio = neg_prio - 1

                    h_score = heuristics.get(neighbor.name, 9999)
                    new_g = turns_taken + neighbor.cost
                    new_f = new_g + h_score

                    heapq.heappush(pq, (
                        new_f, new_prio, new_g, arrival_turn,
                        next(counter), neighbor.name,
                        path + [neighbor] * neighbor.cost
                    ))

        return []

    def get_next_moves(
        self, drones: List[Drone], end_node: Node
    ) -> Dict[int, Node]:
        """Retrieves the next turn's step for each drone."""
        if not self.has_planned:
            self._plan_all_flights(drones, end_node)

        moves: Dict[int, Node] = {}
        for drone in drones:
            if (
                isinstance(drone.location, Node) and
                drone.location.name == end_node.name
            ):
                continue

            plan = self.master_plan.get(drone.id, [])
            if plan:
                next_target = plan[0]
                if drone.location.name != next_target.name:
                    moves[drone.id] = next_target
                self.master_plan[drone.id].pop(0)

        return moves