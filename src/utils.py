from pathlib import Path

import tomlkit

from src.config import Config


CURRENT_DIR = Path(__file__).parent
CONFIG_PATH = CURRENT_DIR / "pyproject.toml"
MEMORY_PATH = CURRENT_DIR / "memory.json"

with open(CONFIG_PATH) as f:
    dct = tomlkit.load(f)

config = Config.model_validate(dct["emby"])


PROXY: str | None = (
    dct["proxy"].unwrap()["proxy"] if dct["proxy"].unwrap()["proxy"] else None
)

RAW_DOWNLOAD_PATH: str = dct["store"].unwrap()["path"]

if RAW_DOWNLOAD_PATH.startswith("."):
    DOWNLOAD_PATH: Path = CURRENT_DIR / RAW_DOWNLOAD_PATH
