"""A-Maze-ing — main entry point.

Usage:
    python3 a_maze_ing.py config.txt
"""

import sys
from parser import parse_config
from maze_generator import MazeGenerator, EAST, SOUTH
from maze_writer import write_maze
from renderer import render_maze


def _grid_to_renderer_format(generator: MazeGenerator) -> list[list[dict]]:
    """Convert integer-encoded grid to renderer's dictionary format.
    
    Args:
        generator: The MazeGenerator instance with a populated grid.
    
    Returns:
        A 2D list of dictionaries with "E" and "S" keys (1 = wall closed, 0 = open).
    """
    maze = []
    for y in range(generator.height):
        row = []
        for x in range(generator.width):
            cell = generator.grid[y][x]
            # Convert bit flags to renderer format
            row.append({
                "E": 1 if (cell & EAST) else 0,
                "S": 1 if (cell & SOUTH) else 0,
            })
        maze.append(row)
    return maze


def main() -> None:
    """Parse config, generate maze, display visualization, write output file.

    Raises:
        SystemExit: On any argument, config, generation, or write error.
    """
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt")
        sys.exit(1)

    # Step 1 — parse config
    config = parse_config(sys.argv[1])

    # Step 2 — generate maze
    generator = MazeGenerator(
        width=config.width,
        height=config.height,
        entry=config.entry,
        exit_=config.exit,
        perfect=config.perfect,
        seed=config.seed,
    )
    generator.generate()

    # Step 3 — display visualization
    maze_display = _grid_to_renderer_format(generator)
    render_maze(maze_display, generator.entry, generator.exit_)

    # Step 4 — write output file
    write_maze(generator, config.output_file)

    print(f"Maze written to '{config.output_file}'.")


if __name__ == "__main__":
    main()
