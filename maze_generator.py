"""Maze generation module for A-Maze-ing project.

This module provides the MazeGenerator class which implements maze generation
using the Recursive Backtracker (DFS) algorithm.

Wall encoding (per cell, 4-bit integer):
    Bit 0 (LSB) = North wall
    Bit 1       = East wall
    Bit 2       = South wall
    Bit 3       = West wall
    1 = wall closed, 0 = wall open

Example usage:
    from maze_generator import MazeGenerator

    gen = MazeGenerator(width=20, height=15, entry=(0, 0), exit=(19, 14),
                        perfect=True, seed=42)
    gen.generate()

    # Access the grid (list of lists of int)
    grid = gen.grid

    # Access the solution path as a string of N/E/S/W
    path = gen.solution

    # Access entry and exit
    entry = gen.entry
    exit_ = gen.exit_
"""

import random
from collections import deque


# Wall bit masks
NORTH: int = 0b0001  # bit 0
EAST: int = 0b0010  # bit 1
SOUTH: int = 0b0100  # bit 2
WEST: int = 0b1000  # bit 3

ALL_WALLS: int = NORTH | EAST | SOUTH | WEST  # 0xF

# Directions: (dx, dy, wall on current cell, opposite wall on neighbor)
DIRECTIONS: list[tuple[int, int, int, int]] = [
    (0, -1, NORTH, SOUTH),
    (1,  0, EAST,  WEST),
    (0,  1, SOUTH, NORTH),
    (-1, 0, WEST,  EAST),
]

# Direction letter for BFS path reconstruction
DIR_LETTER: dict[tuple[int, int], str] = {
    (0, -1): "N",
    (1,  0): "E",
    (0,  1): "S",
    (-1, 0): "W",
}

# "42" pixel pattern (each digit is 5 rows x 3 cols, separated by 1 col)
# 1 = fully walled cell (part of pattern), 0 = normal cell
PATTERN_42: list[list[int]] = [
    [1, 0, 1,  0,  1, 1, 1],
    [1, 0, 1,  0,  0, 0, 1],
    [1, 1, 1,  0,  1, 1, 1],
    [0, 0, 1,  0,  1, 0, 0],
    [0, 0, 1,  0,  1, 1, 1],
]
PATTERN_HEIGHT: int = len(PATTERN_42)       # 5
PATTERN_WIDTH: int = len(PATTERN_42[0])    # 7


class MazeGenerator:
    """Generates a maze using the Recursive Backtracker (DFS) algorithm.

    The maze is stored as a 2D grid where each cell is a 4-bit integer
    encoding which walls are closed (1) or open (0).

    Attributes:
        width: Number of columns.
        height: Number of rows.
        entry: (x, y) entry cell coordinates.
        exit_: (x, y) exit cell coordinates.
        perfect: If True, generates a perfect maze (one unique path).
        seed: Random seed for reproducibility.
        grid: 2D list of ints representing the maze after generation.
        solution: String of N/E/S/W directions from entry to exit.
    """

    def __init__(
        self,
        width: int,
        height: int,
        entry: tuple[int, int],
        exit_: tuple[int, int],
        perfect: bool = True,
        seed: int | None = None,
    ) -> None:
        """Initialize the MazeGenerator with the given parameters.

        Args:
            width: Number of columns in the maze.
            height: Number of rows in the maze.
            entry: (x, y) coordinates of the entry cell.
            exit_: (x, y) coordinates of the exit cell.
            perfect: Whether to generate a perfect maze.
            seed: Optional random seed for reproducible generation.
        """
        self.width = width
        self.height = height
        self.entry = entry
        self.exit_ = exit_
        self.perfect = perfect
        self.seed = seed
        self.grid: list[list[int]] = []
        self.solution: str = ""
        self._visited: list[list[bool]] = []
        self._pattern_cells: set[tuple[int, int]] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> None:
        """Generate the maze.

        Runs the full generation pipeline:
        1. Initialize grid with all walls closed.
        2. Reserve the '42' pattern cells.
        3. Run DFS from the entry cell.
        4. Open entry and exit border walls.
        5. If not perfect, remove extra walls.
        6. Enforce no 3x3 open area rule.
        7. Solve the maze with BFS.
        """
        random.seed(self.seed)
        self._init_grid()
        self._reserve_pattern()
        self._visited[self.entry[1]][self.entry[0]] = True
        self._dfs(self.entry[0], self.entry[1])
        if not self.perfect:
            self._remove_extra_walls()
        self._fix_open_areas()
        self.solution = self._bfs_solve()

    # ------------------------------------------------------------------
    # Grid initialization
    # ------------------------------------------------------------------

    def _init_grid(self) -> None:
        """Initialize the grid with all walls closed and visited map to False.
        Each cell starts with all walls (0xF) and is unvisited.
        """
        self.grid = [
            [ALL_WALLS] * self.width for _ in range(self.height)
        ]
        self._visited = [
            [False] * self.width for _ in range(self.height)
        ]

    # ------------------------------------------------------------------
    # "42" pattern reservation
    # ------------------------------------------------------------------

    def _reserve_pattern(self) -> None:
        """Reserve cells for the '42' pattern before DFS runs.

        Places the pattern roughly centered in the maze.
        Marks reserved cells as visited so DFS skips them,
        and keeps all their walls closed.
        Prints an error and skips if the maze is too small.
        """
        min_width = PATTERN_WIDTH + 4
        min_height = PATTERN_HEIGHT + 4

        if self.width < min_width or self.height < min_height:
            print(
                "Warning: Maze is too small to embed the '42' pattern "
                f"(minimum {min_width}x{min_height} required)."
            )
            return

        # Center the pattern
        origin_x = (self.width - PATTERN_WIDTH) // 2
        origin_y = (self.height - PATTERN_HEIGHT) // 2

        for row_idx, row in enumerate(PATTERN_42):
            for col_idx, cell in enumerate(row):
                if cell == 1:
                    gx = origin_x + col_idx
                    gy = origin_y + row_idx
                    self._visited[gy][gx] = True   # DFS will skip this cell
                    self.grid[gy][gx] = ALL_WALLS  # keep all walls closed
                    self._pattern_cells.add((gx, gy))

    # ------------------------------------------------------------------
    # DFS (Recursive Backtracker) — iterative to avoid recursion limit
    # ------------------------------------------------------------------

    def _dfs(self, start_x: int, start_y: int) -> None:
        """Run iterative DFS from the given start cell to carve passages.

        Uses an explicit stack to avoid Python recursion depth limits
        on large mazes.

        Args:
            start_x: X coordinate of the starting cell.
            start_y: Y coordinate of the starting cell.
        """
        stack: list[tuple[int, int]] = [(start_x, start_y)]

        while stack:
            x, y = stack[-1]
            # Shuffle directions for randomness
            dirs = list(DIRECTIONS)
            random.shuffle(dirs)

            moved = False
            for dx, dy, wall_cur, wall_nbr in dirs:
                nx, ny = x + dx, y + dy
                if self._in_bounds(nx, ny) and not self._visited[ny][nx]:
                    # Carve passage
                    self.grid[y][x] &= ~wall_cur
                    self.grid[ny][nx] &= ~wall_nbr
                    self._visited[ny][nx] = True
                    stack.append((nx, ny))
                    moved = True
                    break

            if not moved:
                stack.pop()

    # ------------------------------------------------------------------
    # Non-perfect mode: remove extra walls
    # ------------------------------------------------------------------

    def _remove_extra_walls(self) -> None:
        """Remove a fraction of internal walls to create loops.

        Skips pattern cells and border walls.
        Removes approximately 15% of internal walls.
        """
        removals = max(1, (self.width * self.height) // 7)
        attempts = 0
        max_attempts = removals * 10

        while removals > 0 and attempts < max_attempts:
            attempts += 1
            x = random.randint(0, self.width - 2)
            y = random.randint(0, self.height - 1)

            if (x, y) in self._pattern_cells:
                continue
            if (x + 1, y) in self._pattern_cells:
                continue

            # Try removing east wall between (x,y) and (x+1,y)
            if self.grid[y][x] & EAST:
                self.grid[y][x] &= ~EAST
                self.grid[y][x + 1] &= ~WEST
                removals -= 1

    # ------------------------------------------------------------------
    # No 3x3 open area enforcement
    # ------------------------------------------------------------------

    def _is_open_area(self, x: int, y: int) -> bool:
        """Check if a 3x3 block starting at (x, y) is fully open.

        A cell is considered 'open to the right' if no East wall,
        and 'open below' if no South wall. We check all interior
        connections in the 3x3 block.

        Args:
            x: Top-left x of the 3x3 block.
            y: Top-left y of the 3x3 block.

        Returns:
            True if the 3x3 area is fully open (no interior walls).
        """
        for row in range(y, y + 3):
            for col in range(x, x + 3):
                if col + 1 < x + 3:
                    if self.grid[row][col] & EAST:
                        return False
                if row + 1 < y + 3:
                    if self.grid[row][col] & SOUTH:
                        return False
        return True

    def _fix_open_areas(self) -> None:
        """Scan and fix any 3x3 fully open areas by adding a wall.

        For each detected open 3x3 block, adds a South wall in the
        center cell (and corresponding North wall below it).
        Skips pattern cells.
        """
        for y in range(self.height - 2):
            for x in range(self.width - 2):
                if self._is_open_area(x, y):
                    # Add wall in center of the 3x3
                    cx, cy = x + 1, y + 1
                    if (cx, cy) not in self._pattern_cells:
                        if cy + 1 < self.height:
                            self.grid[cy][cx] |= SOUTH
                            self.grid[cy + 1][cx] |= NORTH

    # ------------------------------------------------------------------
    # BFS pathfinder
    # ------------------------------------------------------------------

    def _bfs_solve(self) -> str:
        """Find the shortest path from entry to exit using BFS.

        Returns:
            A string of N/E/S/W direction letters representing
            the shortest path from entry to exit.
            Returns empty string if no path exists.
        """
        start = self.entry
        goal = self.exit_
        queue: deque[tuple[int, int]] = deque([start])
        came_from: dict[tuple[int, int], tuple[tuple[int, int], str] | None] = {
            start: None
        }

        while queue:
            x, y = queue.popleft()
            if (x, y) == goal:
                break

            for dx, dy, wall, _ in DIRECTIONS:
                if self.grid[y][x] & wall:
                    continue  # wall is closed
                nx, ny = x + dx, y + dy
                if not self._in_bounds(nx, ny):
                    continue
                if (nx, ny) in came_from:
                    continue
                came_from[(nx, ny)] = ((x, y), DIR_LETTER[(dx, dy)])
                queue.append((nx, ny))

        # Reconstruct path
        if goal not in came_from:
            return ""

        path: list[str] = []
        current: tuple[int, int] = goal
        while came_from[current] is not None:
            prev, letter = came_from[current]  # type: ignore[misc]
            path.append(letter)
            current = prev

        path.reverse()
        return "".join(path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _in_bounds(self, x: int, y: int) -> bool:
        """Check if (x, y) is within the maze grid.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            True if the coordinates are inside the grid.
        """
        return 0 <= x < self.width and 0 <= y < self.height
