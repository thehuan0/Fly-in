import sys
import argparse
from src.parser.map_parser import MapParser
from src.models.drone import Drone
from src.simulation.engine import SimulationEngine
from src.algorithm.swarm_solver import SwarmSolver

try:
    from src.display.gui import GardenGUI
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


def main() -> None:
    """Main execution entry point for the Fly-in simulation."""
    arg_parser = argparse.ArgumentParser(description="Fly-in Drone Simulator")
    arg_parser.add_argument(
        "map_file", type=str, help="Path to the map text file"
    )
    arg_parser.add_argument(
        "--gui", action="store_true", help="Enable the graphical interface"
    )
    args = arg_parser.parse_args()

    parser = MapParser()
    try:
        parser.parse(args.map_file)
    except (ValueError, FileNotFoundError) as e:
        print(e)
        sys.exit(1)

    start_node = parser.start_node
    end_node = parser.end_node

    if start_node is None or end_node is None:
        print("Error: The parsed map is missing a start or end hub.")
        sys.exit(1)

    drones = [
        Drone(id=i, location=start_node)
        for i in range(1, parser.nb_drones + 1)
    ]

    engine = SimulationEngine(drones, end_node)
    solver = SwarmSolver(parser.nodes, parser.connections)

    gui = None
    if args.gui:
        if not GUI_AVAILABLE:
            print("Error: Pygame not installed or gui.py missing.")
            sys.exit(1)
        gui = GardenGUI()

    try:
        while not engine.all_delivered:
            planned_moves = solver.get_next_moves(engine.drones, end_node)
            turn_log = engine.run_turn(planned_moves)

            if turn_log:
                print(turn_log)

            if gui:
                gui.draw(
                    engine,
                    parser.nodes,
                    parser.connections,
                    duration_sec=0.5
                )
    except InterruptedError as e:
        print(f"\nSimulation Aborted: {e}")
        sys.exit(0)
    except Exception as e:
        print(f"Simulation Error: {e}")
        sys.exit(1)

    if gui:
        print("Simulation complete. Close the graphical window to exit.")
        import pygame
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
        pygame.quit()


if __name__ == "__main__":
    main()
