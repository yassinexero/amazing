from config_model import MazeConfig


def parse_config(path: str) -> MazeConfig:
    data: dict = {}

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            key = key.strip().lower()
            value = value.strip()
            if key in ("entry", "exit"):
                x, y = value.split(",")
                data[key] = (int(x), int(y))
            elif key in ("width", "height", "seed"):
                data[key] = int(value)
            elif key == "perfect":
                data[key] = value.lower() == "true"
            else:
                data[key] = value
    return MazeConfig(**data)
