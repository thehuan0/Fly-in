import re
from typing import List, Dict, Optional
from pydantic import ValidationError
from src.models.connection import Connection
from src.models.node import Node, NodeType


class MapParser:
    """
    Parses the simulation map files and constructs the Node/Connection network.
    """
    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.connections: List[Connection] = []
        self.nb_drones: int = 0
        self.start_node: Optional[Node] = None
        self.end_node: Optional[Node] = None

    def _parse_metadata(self, meta_str: Optional[str]) -> Dict[str, str]:
        if not meta_str:
            return {}
        pairs = re.findall(r'(\w+)(?:=([^\]\s,]+))?', meta_str.strip('[]'))
        return {k: v for k, v in pairs}

    def parse(self, file_path: str) -> None:
        """Reads the text file line by line and populates the graph."""
        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.split('#')[0].strip()
                    if not line:
                        continue

                    try:
                        if line.startswith("nb_drones:"):
                            self.nb_drones = int(line.split(":")[1].strip())

                        elif any(
                            line.startswith(p)
                            for p in ["hub:", "start_hub:", "end_hub:"]
                        ):
                            prefix, rest = line.split(":", 1)
                            pattern = (
                                r"(\S+)\s+(-?\d+)\s+(-?\d+)"
                                r"(?:\s+\[(.*)\])?"
                                )
                            match = re.match(pattern, rest.strip())
                            if not match:
                                err = f"Invalid format line {line_num}"
                                raise ValueError(err)

                            name, x_str, y_str, meta_str = match.groups()

                            if "-" in name:
                                raise ValueError(
                                    "Zone names cannot contain dashes"
                                )

                            meta = self._parse_metadata(meta_str)
                            zone_str = meta.get("zone", "normal")

                            try:
                                zone_type = NodeType(zone_str)
                            except ValueError:
                                raise ValueError(
                                    f"Invalid zone type: {zone_str}"
                                )

                            node = Node(
                                name=name,
                                x=int(x_str),
                                y=int(y_str),
                                zone=zone_type,
                                max_drones=int(
                                    meta.get("max_drones", 1)
                                ),
                                color=meta.get("color", "none")
                            )

                            if node.name in self.nodes:
                                raise ValueError(
                                    f"Duplicate node: {node.name}"
                                )
                            self.nodes[node.name] = node

                            if prefix == "start_hub":
                                if self.start_node:
                                    raise ValueError(
                                        "Multiple start hubs detected"
                                    )
                                self.start_node = node
                            elif prefix == "end_hub":
                                if self.end_node:
                                    raise ValueError(
                                        "Multiple end hubs detected"
                                    )
                                self.end_node = node

                        elif line.startswith("connection:"):
                            prefix, rest = line.split(":", 1)
                            pattern = r"(\S+)-(\S+)(?:\s+\[(.*)\])?"
                            match = re.match(pattern, rest.strip())
                            if not match:
                                raise ValueError(
                                    f"Invalid conn line {line_num}"
                                )

                            n1_name, n2_name, meta_str = match.groups()
                            meta = self._parse_metadata(meta_str)

                            if (
                                n1_name not in self.nodes or
                                n2_name not in self.nodes
                            ):
                                raise ValueError(
                                    "Connection uses undefined zones"
                                )

                            conn = Connection(
                                node_a=self.nodes[n1_name],
                                node_b=self.nodes[n2_name],
                                max_link_capacity=int(
                                    meta.get("max_link_capacity", 1)
                                )
                            )

                            if any(
                                c.uid == conn.uid
                                for c in self.connections
                            ):
                                raise ValueError("Duplicate connection")
                            self.connections.append(conn)

                    except ValidationError as e:
                        raise ValueError(f"Error (Line {line_num}):"
                                         f" Invalid map. {e}")
                    except Exception as e:
                        raise ValueError(f"Parsing Error (Line {line_num}):"
                                         f" {e}")

        except FileNotFoundError:
            raise FileNotFoundError(f"Parsing Error: Map file not "
                                    f"found '{file_path}'")
        except Exception as e:
            raise ValueError(f"Parsing Error: {e}")

        # Final structural validations
        if not self.start_node or not self.end_node:
            raise ValueError("Parsing Error: Map must have a "
                             "start_hub and an end_hub")

        if self.nb_drones <= 0:
            raise ValueError("Parsing Error: Map must "
                             "define a positive nb_drones (> 0)")
