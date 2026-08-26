*This project has been created as part of the 42 curriculum by jperez-s.*

# Fly-in

A drone-swarm routing simulator: route a fleet of drones from a start hub to
an end hub across a network of zones in the fewest possible simulation turns,
while respecting per-zone and per-connection capacity limits, zone-type
movement costs, and collision-free turn-by-turn scheduling.

## Description

Fly-in reads a text-based map describing zones (`hub`/`start_hub`/`end_hub`)
and the connections between them, each zone optionally tagged with a type
(`normal`, `priority`, `restricted`, `blocked`), a color, and a capacity. It
then computes a turn-by-turn flight plan for every drone and replays it
through a simulation engine, producing a log of drone movements until every
drone has reached the end hub.

The core problem is multi-agent pathfinding under time and capacity
constraints: drones share zones and connections, restricted zones cost two
turns to enter and cannot be "waited out" mid-transit, and the simulation must
never let two drones violate a zone's `max_drones` or a connection's
`max_link_capacity` on the same turn.

## Instructions

### Install

```bash
make install
```

Creates a local virtual environment and installs `pydantic`, `pygame`, `mypy`,
and `flake8` into it.

### Run

```bash
make run ARGS="path/to/map.txt"
```

Add `--gui` for a graphical view of the simulation:

```bash
make run ARGS="path/to/map.txt --gui"
```

Without `--gui`, the simulation runs headless and prints one line per turn to
the terminal, formatted as `D<id>-<zone>` (or `D<id>-<connection>` for a drone
mid-transit toward a restricted zone), space-separated, e.g.:

```
D1-roof1 D2-corridorA
D1-roof2 D2-tunnelB
D1-goal D2-goal
```

### Debug

```bash
make debug ARGS="path/to/map.txt"
```

Runs the simulation under Python's built-in debugger (`pdb`).

### Lint

```bash
make lint          # flake8 + mypy with the mandatory flag set
make lint-strict    # flake8 + mypy --strict
```

### Clean

```bash
make clean
```

Removes `__pycache__`, `.mypy_cache`, and the virtual environment.

### Map file format

```
nb_drones: 5
start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
connection: hub-roof1
connection: hub-corridorA
connection: corridorA-goal [max_link_capacity=2]
```

- `zone=` — `normal` (default, 1 turn), `priority` (1 turn, preferred by the
  planner), `restricted` (2 turns, cannot be left mid-transit), or `blocked`
  (impassable).
- `max_drones=` — how many drones a zone may hold at once (default 1; the
  start and end hubs are exempt from this limit).
- `max_link_capacity=` — how many drones may traverse a connection
  simultaneously (default 1).
- Lines starting with `#` are comments.

## Algorithm & Implementation Strategy

**Parsing** (`src/parser/map_parser.py`) reads the map line by line, building
`Node` and `Connection` objects (Pydantic models with field validation for
positive capacities, valid zone types, and unique names/connections), and
surfaces a line-numbered error message on malformed input.

**Pathfinding** (`src/simulation/swarm_solver.py`) treats the problem as
search over a *time-expanded graph*: every state is `(zone, turn)`, not just
`zone`. For each drone, a single-agent A* search explores three actions per
state — move to a neighboring zone, wait in place, or (for a restricted
target) commit to a forced two-turn transit — while consulting shared
reservation tables (`node_reservations`, `link_reservations`) to reject moves
that would exceed a zone's or connection's capacity at that turn.

Because planning every drone independently and simultaneously is what causes
collisions, drones are planned **one at a time in priority order**, each one
reserving its turn-by-turn occupancy before the next drone is planned (a
prioritized/cooperative-pathfinding approach). Since a poor ordering can
produce an unnecessarily long plan — or even leave a drone stuck — the planner
tries multiple random orderings and keeps the best result found.

The full plan is computed once, cached, and replayed turn-by-turn by
`SimulationEngine` (`src/simulation/engine.py`), which applies a drone's
move, frees its old zone's capacity, and lands any drones whose two-turn
restricted transit has elapsed — all before the next turn's moves are
considered, matching the "movers free up space the same turn" rule.

**Complexity:** each single-drone A* search is bounded by the size of the
time-expanded graph it explores from that drone's starting state; the
multi-restart outer loop runs a fixed number of times. The expensive part of
planning happens once at the start of the simulation, not on every turn —
after that, advancing a turn is just a dictionary lookup per drone.

> See `CODE_REVIEW.md` for a detailed walkthrough of where this approach is
> strong (capacity correctness, verified independently) and where it currently
> falls short (the stopping heuristic, plus a handful of crash/hang edge cases
> that should be fixed before submission).

## Visual Representation

`gui.py` renders the map and live drone positions with `pygame`: zones are
drawn as themed sprites (or colored circles if sprite assets aren't present),
connections as lines between them, and drones animate smoothly between
positions each turn using eased interpolation. A HUD shows the current turn
count and delivered/total drone count. When no `--gui` flag is passed, the
simulation runs headless and prints the same information as a plain text log
instead.

## Resources

- Silver, D. (2005). *Cooperative Pathfinding* — the prioritized,
  time-expanded-graph approach this project's solver is based on.
- Hart, Nilsson, Raphael (1968). *A Formal Basis for the Heuristic
  Determination of Minimum Cost Paths* — the original A* paper.
- [Pydantic documentation](https://docs.pydantic.dev/) — model validation.
- [Pygame documentation](https://www.pygame.org/docs/) — rendering.
- [mypy documentation](https://mypy.readthedocs.io/) /
  [flake8 documentation](https://flake8.pycqa.org/) — static analysis tooling.

### AI usage

*(Draft — replace with an accurate, first-person account of your own process
before submitting; the subject explicitly grades your ability to explain any
AI-assisted part of this project.)*

AI assistance (Claude) was used for: reviewing the overall codebase structure
and flagging logic/clarity issues; iterating on the pygame-based GUI
(including the geometric-shape fallback rendering for missing sprite assets);
and debugging specific pieces of the simulation engine and pathfinding logic.
All AI-suggested code was read, tested, and adjusted before being kept —
nothing was used without understanding what it does and why.
