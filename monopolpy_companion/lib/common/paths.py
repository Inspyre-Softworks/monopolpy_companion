from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PACKAGE_ROOT / "conf"
DEFAULT_CONFIG_FILE = CONFIG_DIR / "default.yml"
APP_DATA_DIR = Path.home() / "Documents" / "Games" / "Monopolpy_Companion"
USER_CONFIG_FILE = APP_DATA_DIR / "config.yml"
SAVE_DIR = APP_DATA_DIR / "saves"
DATABASE_DIR = APP_DATA_DIR / "databases"
PLAYER_DB_FILE = DATABASE_DIR / "players.yml"


def ensure_runtime_dirs() -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
