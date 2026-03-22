RESET = "\033[0m"

COLORS = {
    "white": "\033[37m",
    "red": "\033[31m",
    "green": "\033[32m",
    "blue": "\033[34m",
    "yellow": "\033[33m"
}


def render_maze(maze, entry, exit, wall_color="white"):
    height = len(maze)
    width = len(maze[0])

    color = COLORS.get(wall_color, COLORS["white"])

    # top border
    print(color + "+" + "---+" * width + RESET)

    for y in range(height):

        # vertical walls
        line = color + "|" + RESET

        for x in range(width):

            if (x, y) == entry:
                cell_char = COLORS["green"] + " S " + RESET
            elif (x, y) == exit:
                cell_char = COLORS["yellow"] + " E " + RESET
            else:
                cell_char = "   "

            if maze[y][x]["E"]:
                line += cell_char + color + "|" + RESET
            else:
                line += cell_char + " "

        print(line)

        # bottom walls
        line = color + "+"
        for x in range(width):
            if maze[y][x]["S"]:
                line += "---+"
            else:
                line += "   +"

        print(line + RESET)
