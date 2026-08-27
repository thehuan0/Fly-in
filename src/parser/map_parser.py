import re
from typing import List, Dict, Optional
from pydantic import ValidationError
from src.models.connection import Connection
from src.models.node import Node, NodeType


class MapParser:
    """Parses the simulation map files and constructs the graph network."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.connections: List[Connection] = []
        self.nb_drones: int = 0
        self.start_node: Optional[Node] = None
        self.end_node: Optional[Node] = None

    def _parse_metadata(self, meta_str: Optional[str]) -> Dict[str, str]:
        """Parses bracketed metadata, handling space and '=' separators."""
        if not meta_str:
            return {}

        clean_str = meta_str.strip('[] ')
        if not clean_str:
            return {}

        tokens = clean_str.split()
        result: Dict[str, str] = {}
        i = 0

        while i < len(tokens):
            token = tokens[i]
            if '=' in token:
                k, v = token.split('=', 1)
                result[k] = v
                i += 1
            else:
                if i + 1 < len(tokens) and '=' not in tokens[i + 1]:
                    result[token] = tokens[i + 1]
                    i += 2
                else:
                    result[token] = "true"
                    i += 1

        return result

    def parse(self, file_path: str) -> None:
        """Reads the text file line by line and populates the graph."""
        try:
            with open(file_path, 'r') as f:
                for line_num, raw_line in enumerate(f, 1):
                    line = raw_line.split('#')[0].strip()
                    if not line:
                        continue

                    try:
                        self._process_line(line, line_num)
                    except ValidationError as e:
                        raise ValueError(
                            f"Error (Line {line_num}): Invalid map. {e}"
                        )
                    except Exception as e:
                        raise ValueError(
                            f"Parsing Error (Line {line_num}): {e}"
                        )
        except FileNotFoundError:
            raise FileNotFoundError(f"Map file not found '{file_path}'")
        except Exception as e:
            raise ValueError(f"Parsing Error: {e}")

        self._validate_structure()

    def _process_line(self, line: str, line_num: int) -> None:
        """Processes a single line of the map file."""
        if line.startswith("nb_drones:"):
            self.nb_drones = int(line.split(":")[1].strip())

        elif any(
            line.startswith(p) for p in ["hub:", "start_hub:", "end_hub:"]
        ):
            self._parse_node(line, line_num)

        elif line.startswith("connection:"):
            self._parse_connection(line, line_num)

    def _parse_node(self, line: str, line_num: int) -> None:
        """Parses and stores a Node from a map line."""
        prefix, rest = line.split(":", 1)
        pattern = r"(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.*)\])?"
        match = re.match(pattern, rest.strip())
        if not match:
            raise ValueError(f"Invalid format line {line_num}")

        name, x_str, y_str, meta_str = match.groups()
        if "-" in name:
            raise ValueError("Zone names cannot contain dashes")

        meta = self._parse_metadata(meta_str)
        zone_str = meta.get("zone", "normal")

        try:
            zone_type = NodeType(zone_str)
        except ValueError:
            raise ValueError(f"Invalid zone type: {zone_str}")

        node = Node(
            name=name,
            x=int(x_str),
            y=int(y_str),
            zone=zone_type,
            max_drones=int(meta.get("max_drones", 1)),
            color=meta.get("color", "none")
        )

        if node.name in self.nodes:
            raise ValueError(f"Duplicate node: {node.name}")
        self.nodes[node.name] = node

        if prefix == "start_hub":
            if self.start_node:
                raise ValueError("Multiple start hubs detected")
            self.start_node = node
        elif prefix == "end_hub":
            if self.end_node:
                raise ValueError("Multiple end hubs detected")
            self.end_node = node

    def _parse_connection(self, line: str, line_num: int) -> None:
        """Parses and stores a Connection from a map line."""
        _, rest = line.split(":", 1)
        pattern = r"(\S+)-(\S+)(?:\s+\[(.*)\])?"
        match = re.match(pattern, rest.strip())
        if not match:
            raise ValueError(f"Invalid conn line {line_num}")

        n1_name, n2_name, meta_str = match.groups()
        meta = self._parse_metadata(meta_str)

        if n1_name not in self.nodes or n2_name not in self.nodes:
            raise ValueError("Connection uses undefined zones")

        conn = Connection(
            node_a=self.nodes[n1_name],
            node_b=self.nodes[n2_name],
            max_link_capacity=int(meta.get("max_link_capacity", 1))
        )

        if any(c.uid == conn.uid for c in self.connections):
            raise ValueError("Duplicate connection")
        self.connections.append(conn)

    def _validate_structure(self) -> None:
        """Final validations to ensure a solvable state."""
        if not self.start_node or not self.end_node:
            raise ValueError(
                "Parsing Error: Map must have a start_hub and an end_hub"
            )
        if self.nb_drones <= 0:
            raise ValueError(
                "Parsing Error: Map must define a positive nb_drones (> 0)"
            )
