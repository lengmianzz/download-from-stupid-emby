from pathlib import Path

import tomlkit

from src.config import Config
from src.errors import LackConfigError


CURRENT_DIR = Path(__file__).parent
CONFIG_PATH = CURRENT_DIR / "pyproject.toml"   
MEMORY_PATH = CURRENT_DIR / "memory.json" 

with open(CONFIG_PATH) as f:
    dct = tomlkit.load(f)

config = Config.model_validate(dct["emby"])

if not all([config.host, config.user_name, config.password]):
    raise LackConfigError("[-]请填写完配置再运行项目")

PROXY: str | None = dct["proxy"].unwrap()["proxy"] if dct["proxy"].unwrap()["proxy"] else None

RAW_DOWNLOAD_PATH: str = dct["store"].unwrap()["path"]

if RAW_DOWNLOAD_PATH.startswith("."):
    DOWNLOAD_PATH: Path = CURRENT_DIR / RAW_DOWNLOAD_PATH
