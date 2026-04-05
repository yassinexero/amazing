"""Shared constants for A-Maze-ing project.

Imported by config_parser.py, maze_generator.py, and maze_visual.py.
"""

# ── Wall bit masks ────────────────────────────────────────────────────────────
NORTH: int = 0b0001  # bit 0
EAST:  int = 0b0010  # bit 1
SOUTH: int = 0b0100  # bit 2
WEST:  int = 0b1000  # bit 3

ALL_WALLS: int = NORTH | EAST | SOUTH | WEST  # 0xF

# ── Directions ────────────────────────────────────────────────────────────────
# Each tuple: (dx, dy, wall on current cell, wall on neighbor)
DIRECTIONS: list[tuple[int, int, int, int]] = [
    (0, -1, NORTH, SOUTH),
    (1,  0, EAST,  WEST),
    (0,  1, SOUTH, NORTH),
    (-1, 0, WEST,  EAST),
]

# Maps movement vector → direction letter (used in BFS path reconstruction)
DIR_LETTER: dict[tuple[int, int], str] = {
    (0, -1): "N",
    (1,  0): "E",
    (0,  1): "S",
    (-1, 0): "W",
}

# ── "42" pixel pattern ────────────────────────────────────────────────────────
# 7 rows x 9 cols. 1 = solid walled cell, 0 = normal cell DFS can carve.
# Col 4 (all zeros) is the gap between the "4" and the "2".
#
#   4   4  .  2222
#   4   4  .  2  2
#   4   4  .     2
#   44444  .  2222
#       4  .  2
#       4  .  2
#       4  .  2222
#
PATTERN_42: list[list[int]] = [
    [1, 0, 1,  0,  1, 1, 1],
    [1, 0, 1,  0,  0, 0, 1],
    [1, 1, 1,  0,  1, 1, 1],
    [0, 0, 1,  0,  1, 0, 0],
    [0, 0, 1,  0,  1, 1, 1],
]

PATTERN_HEIGHT: int = len(PATTERN_42)      # 5
PATTERN_WIDTH:  int = len(PATTERN_42[0])   # 7

# Minimum maze size to fit the pattern with 2-cell buffer on each side
MIN_MAZE_WIDTH:  int = PATTERN_WIDTH  + 2  # 9
MIN_MAZE_HEIGHT: int = PATTERN_HEIGHT + 2  # 7


def pattern_cells(maze_width: int, maze_height: int) -> set[tuple[int, int]]:
    """Return the set of grid coordinates occupied by the '42' pattern.

    The pattern is centered in the maze using integer division.

    Args:
        maze_width:  Number of columns in the maze.
        maze_height: Number of rows in the maze.

    Returns:
        Set of (x, y) coordinates that belong to the '42' pattern.
    """
    origin_x = (maze_width  - PATTERN_WIDTH)  // 2
    origin_y = (maze_height - PATTERN_HEIGHT) // 2
    cells: set[tuple[int, int]] = set()
    for row_idx, row in enumerate(PATTERN_42):
        for col_idx, cell in enumerate(row):
            if cell == 1:
                cells.add((origin_x + col_idx, origin_y + row_idx))
    return cells
