"""Reading and writing of organisation rules (default and user YAML)."""
from pathlib import Path

import yaml

from src.config.rules import RulesConfig
from src.utils.paths import CONFIG_DIR

DEFAULT_RULES_PATH = CONFIG_DIR / "default_rules.yaml"
USER_RULES_PATH = CONFIG_DIR / "user_rules.yaml"


def _read_yaml(path: Path):
    """Return the parsed YAML at ``path``, or ``None`` if it does not exist."""
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_config(
    default_path: Path = DEFAULT_RULES_PATH,
    user_path: Path = USER_RULES_PATH,
) -> RulesConfig:
    """Load the active rules: the user's file if present, else the defaults."""
    data = _read_yaml(user_path)
    if data is None:
        data = _read_yaml(default_path)
    return RulesConfig.from_dict(data or {})


def save_user_config(config: RulesConfig, user_path: Path = USER_RULES_PATH) -> None:
    """Persist the user's rules to YAML, leaving the shipped defaults intact."""
    user_path.parent.mkdir(parents=True, exist_ok=True)
    with user_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config.to_dict(), handle, default_flow_style=False, sort_keys=False)


def export_config(config: RulesConfig, path: Path) -> None:
    """Write the shareable rules (categories + sorting) to ``path``; watch folders omitted."""
    data = config.to_dict()
    data.pop("watch", None)
    with Path(path).open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, default_flow_style=False, sort_keys=False)


def import_config(path: Path) -> RulesConfig:
    """Load a rules config from an arbitrary YAML file (watch left at defaults)."""
    return RulesConfig.from_dict(_read_yaml(Path(path)) or {})
