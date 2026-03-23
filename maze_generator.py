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

    gen = MazeGenerator(width=20, height=15, entry=(0, 0), exit_=(19, 14),
                        perfect=True, seed=42)
    gen.generate()

    grid     = gen.grid      # 2D list of hex wall values
    path     = gen.solution  # "EESSENWW..." direction string
    entry    = gen.entry     # (x, y)
    exit_    = gen.exit_     # (x, y)
"""

import random
from collections import deque

from constants import (
    NORTH, EAST, SOUTH, WEST,
    ALL_WALLS,
    DIRECTIONS,
    DIR_LETTER,
    PATTERN_42,
    PATTERN_HEIGHT,
    PATTERN_WIDTH,
    pattern_cells,
)


class MazeGenerator:
    """Generates a maze using the Recursive Backtracker (DFS) algorithm.

    The maze is stored as a 2D grid where each cell is a 4-bit integer
    encoding which walls are closed (1) or open (0).

    Attributes:
        width:          Number of columns.
        height:         Number of rows.
        entry:          (x, y) entry cell coordinates.
        exit_:          (x, y) exit cell coordinates.
        perfect:        If True, generates a perfect maze (one unique path).
        seed:           Random seed for reproducibility.
        grid:           2D list of ints representing the maze after generation.
        solution:       String of N/E/S/W directions from entry to exit.
        _visited:       2D bool grid tracking which cells DFS has carved.
        _pattern_cells: Set of (x, y) coords belonging to the "42" pattern.
    """

    def __init__(
        self,
        width:   int,
        height:  int,
        entry:   tuple[int, int],
        exit_:   tuple[int, int],
        perfect: bool = True,
        seed:    int | None = None,
    ) -> None:
        """Initialize the MazeGenerator.

        Args:
            width:   Number of columns in the maze.
            height:  Number of rows in the maze.
            entry:   (x, y) coordinates of the entry cell.
            exit_:   (x, y) coordinates of the exit cell.
            perfect: Whether to generate a perfect maze.
            seed:    Optional random seed for reproducible generation.
        """
        self.width   = width
        self.height  = height
        self.entry   = entry
        self.exit_   = exit_
        self.perfect = perfect
        self.seed    = seed

        self.grid:           list[list[int]]          = []
        self.solution:       str                      = ""
        self._visited:       list[list[bool]]         = []
        self._pattern_cells: set[tuple[int, int]]     = set()

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self) -> None:
        """Generate the maze.

        Pipeline:
        1. Initialize grid — all walls closed.
        2. Reserve "42" pattern cells so DFS skips them.
        3. Run DFS from entry to carve passages.
        4. Remove extra walls if not perfect mode.
        5. Fix any 3×3 fully open areas.
        6. Solve with BFS to get the shortest path.
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

    # ── Grid initialization ───────────────────────────────────────────────────

    def _init_grid(self) -> None:
        """Initialize the grid with all walls closed and visited map False."""
        self.grid = [
            [ALL_WALLS] * self.width for _ in range(self.height)
        ]
        self._visited = [
            [False] * self.width for _ in range(self.height)
        ]

    # ── "42" pattern reservation ──────────────────────────────────────────────

    def _reserve_pattern(self) -> None:
        """Reserve "42" pattern cells before DFS runs.

        Marks each pattern cell as visited (so DFS skips it) and keeps
        all its walls closed. Size is guaranteed valid by config_parser.
        """
        self._pattern_cells = pattern_cells(self.width, self.height)
        for gx, gy in self._pattern_cells:
            self._visited[gy][gx] = True
            self.grid[gy][gx]     = ALL_WALLS

    # ── DFS ───────────────────────────────────────────────────────────────────

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
            dirs = list(DIRECTIONS)
            random.shuffle(dirs)

            moved = False
            for dx, dy, wall_cur, wall_nbr in dirs:
                nx, ny = x + dx, y + dy
                if self._in_bounds(nx, ny) and not self._visited[ny][nx]:
                    self.grid[y][x]   &= ~wall_cur
                    self.grid[ny][nx] &= ~wall_nbr
                    self._visited[ny][nx] = True
                    stack.append((nx, ny))
                    moved = True
                    break

            if not moved:
                stack.pop()

    # ── Non-perfect mode ──────────────────────────────────────────────────────

    def _remove_extra_walls(self) -> None:
        """Remove ~15% of internal walls to create loops.

        Skips pattern cells. Removes only East walls (and matching West
        on the neighbor) to keep the logic simple.
        """
        removals    = max(1, (self.width * self.height) // 7)
        attempts    = 0
        max_attempts = removals * 10

        while removals > 0 and attempts < max_attempts:
            attempts += 1
            x = random.randint(0, self.width - 2)
            y = random.randint(0, self.height - 1)

            if (x, y) in self._pattern_cells:
                continue
            if (x + 1, y) in self._pattern_cells:
                continue

            if self.grid[y][x] & EAST:
                self.grid[y][x]     &= ~EAST
                self.grid[y][x + 1] &= ~WEST
                removals -= 1

    # ── 3×3 open area fix ────────────────────────────────────────────────────

    def _is_open_area(self, x: int, y: int) -> bool:
        """Return True if the 3×3 block at (x, y) has no interior walls.

        Args:
            x: Top-left x of the 3×3 block.
            y: Top-left y of the 3×3 block.
        """
        for row in range(y, y + 3):
            for col in range(x, x + 3):
                if col + 1 < x + 3 and self.grid[row][col] & EAST:
                    return False
                if row + 1 < y + 3 and self.grid[row][col] & SOUTH:
                    return False
        return True

    def _fix_open_areas(self) -> None:
        """Add a South wall at the center of any fully open 3×3 block."""
        for y in range(self.height - 2):
            for x in range(self.width - 2):
                if self._is_open_area(x, y):
                    cx, cy = x + 1, y + 1
                    if (cx, cy) not in self._pattern_cells:
                        if cy + 1 < self.height:
                            self.grid[cy][cx]     |= SOUTH
                            self.grid[cy + 1][cx] |= NORTH

    # ── BFS solver ───────────────────────────────────────────────────────────

    def _bfs_solve(self) -> str:
        """Find the shortest path from entry to exit using BFS.

        Returns:
            A string of N/E/S/W direction letters (shortest path),
            or an empty string if no path exists.
        """
        start = self.entry
        goal  = self.exit_
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
                    continue
                nx, ny = x + dx, y + dy
                if not self._in_bounds(nx, ny):
                    continue
                if (nx, ny) in came_from:
                    continue
                came_from[(nx, ny)] = ((x, y), DIR_LETTER[(dx, dy)])
                queue.append((nx, ny))

        # Reconstruct path by walking came_from backwards
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

    # ── Helper ────────────────────────────────────────────────────────────────

    def _in_bounds(self, x: int, y: int) -> bool:
        """Return True if (x, y) is inside the maze grid.

        Args:
            x: Column index.
            y: Row index.
        """
        return 0 <= x < self.width and 0 <= y < self.height
