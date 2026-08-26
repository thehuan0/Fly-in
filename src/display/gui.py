import pygame
import os
from typing import Dict, List, Tuple, Union, Any
from src.simulation.engine import SimulationEngine
from src.models.node import Node, NodeType
from src.models.connection import Connection


class GardenGUI:
    """Handles the graphical representation of the simulation."""
    def __init__(self, width: int = 1400, height: int = 900) -> None:
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode(
            (self.width, self.height), pygame.RESIZABLE
        )
        pygame.display.set_caption("Fly-in: Bee Swarm Simulator")

        self.font_large = pygame.font.SysFont("Segoe UI, Arial", 24, bold=True)
        self.font_medium = pygame.font.SysFont(
            "Segoe UI, Arial", 16, bold=True
        )
        self.font_small = pygame.font.SysFont("Segoe UI, Arial", 10, bold=True)

        self.colors: Dict[Union[str, NodeType], Tuple[int, ...]] = {
            "bg": (88, 145, 75),
            "line": (0, 0, 0),
            "text": (255, 255, 255),
            "start": (166, 227, 161),
            "goal": (249, 226, 175),
            "drone": (250, 179, 135),
            "drone_transit": (243, 139, 168),
            NodeType.NORMAL: (137, 180, 250),
            NodeType.RESTRICTED: (243, 139, 168),
            NodeType.PRIORITY: (148, 226, 213),
            NodeType.BLOCKED: (108, 112, 134)
        }

        self.scale_x = 1.0
        self.scale_y = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.current_spots: Dict[int, Tuple[int, int]] = {}

        self.raw_sprites: Dict[str, pygame.Surface] = {}
        self.scaled_sprites: Dict[str, pygame.Surface] = {}
        self.last_radius = 0
        self._load_raw_sprites()

    def _load_raw_sprites(self) -> None:
        asset_map = {
            "bee": "assets/bee.png",
            "beehive": "assets/beehive.png",
            "flower": "assets/flower.png",
            "priority": "assets/flower_priority.png",
            "spider": "assets/spider.png",
            "toast": "assets/toast.png",
            "sign": "assets/sign.png"
        }
        for name, path in asset_map.items():
            if os.path.exists(path):
                surf = pygame.image.load(path).convert_alpha()
                self.raw_sprites[name] = surf

    def _update_scaled_sprites(
        self, node_radius: int, drone_radius: int
    ) -> None:
        if self.last_radius == node_radius:
            return
        self.last_radius = node_radius

        for name, raw in self.raw_sprites.items():
            if raw and name != "sign":
                size = int(node_radius * 2.5)
                if name == "bee":
                    size = int(drone_radius * 2.5)
                elif name == "beehive":
                    size = int(node_radius * 3.5)
                self.scaled_sprites[name] = pygame.transform.scale(
                    raw, (size, size)
                )

    def _parse_color(self, color_str: str) -> Tuple[int, int, int]:
        colors_map = {
            "red": (214, 93, 104), "blue": (118, 159, 229),
            "green": (132, 191, 110), "yellow": (229, 194, 108),
            "gray": (140, 140, 140), "black": (40, 40, 40),
            "white": (240, 240, 240), "purple": (174, 118, 229),
            "orange": (229, 146, 108)
        }
        return colors_map.get(color_str.lower(), (45, 45, 55))

    def _draw_text_with_box(
        self,
        text: str,
        font: pygame.font.Font,
        text_color: Tuple[int, int, int],
        box_color: Tuple[int, int, int],
        pos: Tuple[int, int],
        center: bool = True
    ) -> None:
        text_surf = font.render(text, True, text_color)
        if center:
            bg_rect = text_surf.get_rect(center=pos)
        else:
            bg_rect = text_surf.get_rect(topleft=pos)

        bg_rect.inflate_ip(12, 8)
        pygame.draw.rect(self.screen, box_color, bg_rect, border_radius=4)
        pygame.draw.rect(
            self.screen, (20, 20, 30), bg_rect, width=2, border_radius=4
        )
        text_rect = text_surf.get_rect(center=bg_rect.center)
        self.screen.blit(text_surf, text_rect)

    def _fit_view(self, nodes: Dict[str, Node]) -> None:
        if not nodes:
            return
        xs = [n.x for n in nodes.values()]
        ys = [n.y for n in nodes.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        grid_w = max(max_x - min_x, 1)
        grid_h = max(max_y - min_y, 1)
        self.scale_x = min((self.width * 0.85) / grid_w, 150.0)
        self.scale_y = min((self.height * 0.75) / grid_h, 150.0)
        self.offset_x = min_x + grid_w / 2.0
        self.offset_y = min_y + grid_h / 2.0

    def _get_pos(self, x: int, y: int) -> Tuple[int, int]:
        px = (self.width / 2) + (x - self.offset_x) * self.scale_x
        py = (self.height / 2) - (y - self.offset_y) * self.scale_y
        return (int(px), int(py))

    def _get_parking_spots(
        self,
        engine: SimulationEngine,
        node_positions: Dict[str, Tuple[int, int]],
        radius: int
    ) -> Dict[int, Tuple[int, int]]:
        spots: Dict[int, Tuple[int, int]] = {}
        groups: Dict[str, List[Any]] = {}
        for drone in engine.drones:
            if drone.id in engine.delivered_ids:
                loc = engine.end_node.name
            elif drone.id in engine.in_transit:
                t_name = engine.in_transit[drone.id].name
                loc = f"transit|{t_name}|{drone.location.name}"
            else:
                loc = drone.location.name
            groups.setdefault(loc, []).append(drone)

        dr = max(6, int(radius * 0.35))
        for key, drones_in_group in groups.items():
            drones_in_group.sort(key=lambda d: d.id)
            n_drones = len(drones_in_group)

            if key.startswith("transit|"):
                parts = key.split("|")
                p1 = node_positions[parts[2]]
                p2 = node_positions[parts[1]]
                base_x = (p1[0] + p2[0]) // 2
                base_y = (p1[1] + p2[1]) // 2
                cols = min(n_drones, 3)
            else:
                base_x, base_y = node_positions[key]
                cols = min(n_drones, 5)

            rows = (n_drones + cols - 1) // cols
            for i, drone in enumerate(drones_in_group):
                col_idx = i % cols
                row_idx = i // cols
                offset_x = (col_idx - (cols - 1) / 2.0) * (dr * 1.5)
                offset_y = (row_idx - (rows - 1) / 2.0) * (dr * 1.5)
                spots[drone.id] = (
                    int(base_x + offset_x), int(base_y + offset_y)
                )

        return spots

    def draw(
        self,
        engine: SimulationEngine,
        garden_nodes: Dict[str, Node],
        connections: List[Connection],
        duration_sec: float = 1.0
    ) -> None:
        self.width, self.height = self.screen.get_size()
        self._fit_view(garden_nodes)
        node_positions = {
            name: self._get_pos(n.x, n.y) for name, n in garden_nodes.items()
        }

        base_scale = min(self.scale_x, self.scale_y)
        radius = max(16, min(32, int(base_scale * 0.35)))
        dr = max(8, int(radius * 0.4))
        self._update_scaled_sprites(radius, dr)

        if not self.current_spots:
            s_name = next(
                (n for n in garden_nodes if "start" in n.lower()),
                list(garden_nodes.keys())[0]
            )
            self.current_spots = {
                d.id: node_positions[s_name] for d in engine.drones
            }

        target_spots = self._get_parking_spots(
            engine, node_positions, radius
        )

        frames = int(60 * duration_sec)

        for frame in range(frames + 1):
            t = frame / frames if frames > 0 else 1.0
            ease_t = t * t * (3.0 - 2.0 * t)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise InterruptedError("GUI window closed by user.")

            bg_col = self.colors.get("bg")
            if isinstance(bg_col, tuple) and len(bg_col) == 3:
                self.screen.fill(bg_col)

            for conn in connections:
                pa = node_positions.get(conn.node_a.name)
                pb = node_positions.get(conn.node_b.name)
                if pa and pb:
                    line_col = self.colors.get("line")
                    if isinstance(line_col, tuple) and len(line_col) == 3:
                        pygame.draw.line(self.screen, line_col, pa, pb, 4)

            for name, node in garden_nodes.items():
                pos = node_positions.get(name)
                if not pos:
                    continue

                if name == engine.end_node.name or "start" in name.lower():
                    sprite_name = "beehive"
                elif node.node_type == NodeType.PRIORITY:
                    sprite_name = "priority"
                elif node.node_type == NodeType.RESTRICTED:
                    sprite_name = "toast"
                elif node.node_type == NodeType.BLOCKED:
                    sprite_name = "spider"
                else:
                    sprite_name = "flower"

                surf = self.scaled_sprites.get(sprite_name)
                if surf:
                    self.screen.blit(surf, surf.get_rect(center=pos))
                else:
                    if name == engine.end_node.name:
                        color = self.colors["goal"]
                    elif "start" in name.lower():
                        color = self.colors["start"]
                    else:
                        color = self.colors.get(
                            node.node_type, self.colors[NodeType.NORMAL]
                        )

                    if isinstance(color, tuple) and len(color) == 3:
                        shadow = (color[0]//2, color[1]//2, color[2]//2, 50)
                        pygame.draw.circle(
                            self.screen, shadow, (pos[0]+2, pos[1]+2), radius+2
                        )
                        pygame.draw.circle(self.screen, color, pos, radius)
                        pygame.draw.circle(
                            self.screen, (255, 255, 255), pos, radius, 2
                        )

                box_color = self._parse_color(node.color or "none")
                self._draw_text_with_box(
                    name, self.font_small, (255, 255, 255),
                    box_color, (pos[0], pos[1] + radius + 14)
                )

            for drone in engine.drones:
                start_pos = self.current_spots.get(
                    drone.id, target_spots[drone.id]
                )
                end_pos = target_spots.get(drone.id, start_pos)
                px = int(start_pos[0] + (end_pos[0] - start_pos[0]) * ease_t)
                py = int(start_pos[1] + (end_pos[1] - start_pos[1]) * ease_t)

                bee_surf = self.scaled_sprites.get("bee")
                if bee_surf:
                    if end_pos[0] < start_pos[0]:
                        bee_surf = pygame.transform.flip(bee_surf, True, False)
                    self.screen.blit(
                        bee_surf, bee_surf.get_rect(center=(px, py))
                    )
                else:
                    is_transit = drone.id in engine.in_transit
                    fill = self.colors[
                        "drone_transit" if is_transit else "drone"
                    ]
                    if isinstance(fill, tuple) and len(fill) == 3:
                        pygame.draw.circle(
                            self.screen, (10, 10, 15), (px+1, py+1), dr
                        )
                        pygame.draw.circle(self.screen, fill, (px, py), dr)

                if dr >= 5:
                    self._draw_text_with_box(
                        str(drone.id), self.font_small,
                        (255, 255, 255), (40, 40, 50),
                        (px, py - dr - 12)
                    )

            sign_raw = self.raw_sprites.get("sign")
            if sign_raw:
                sign_scaled = pygame.transform.scale(sign_raw, (240, 110))
                self.screen.blit(sign_scaled, (15, 15))

                t1 = self.font_large.render(
                    f"Turn: {engine.turn}", True, (0, 0, 0)
                )
                d_count = len(engine.delivered_ids)
                t_count = len(engine.drones)
                t2 = self.font_medium.render(
                    f"Delivered: {d_count} / {t_count}", True, (0, 0, 0)
                )
                self.screen.blit(t1, (45, 35))
                self.screen.blit(t2, (45, 70))
            else:
                hud_surf = pygame.Surface((220, 80), pygame.SRCALPHA)
                hud_surf.fill((30, 30, 46, 200))
                self.screen.blit(hud_surf, (15, 15))

                line_col = self.colors.get("line")
                if isinstance(line_col, tuple) and len(line_col) == 3:
                    pygame.draw.rect(
                        self.screen, line_col,
                        pygame.Rect(15, 15, 220, 80), width=2, border_radius=4
                    )

                c_text = self.colors.get("text")
                c_goal = self.colors.get("goal")
                if (isinstance(c_text, tuple) and len(c_text) == 3 and
                        isinstance(c_goal, tuple) and len(c_goal) == 3):
                    self._draw_text_with_box(
                        f"Turn: {engine.turn}", self.font_large,
                        c_text, (45, 45, 55), (30, 25), center=False
                    )
                    d_str = f"Delivered: {len(engine.delivered_ids)} / " \
                            f"{len(engine.drones)}"
                    self._draw_text_with_box(
                        d_str, self.font_medium, c_goal,
                        (45, 45, 55), (30, 55), center=False
                    )

            pygame.display.flip()
            pygame.time.wait(int(1000 / 60))

        self.current_spots = target_spots
