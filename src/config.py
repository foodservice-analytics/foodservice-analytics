"""Загрузка YAML-конфига и подстановка env-переменных."""
import os
from pathlib import Path
import yaml


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_config_path"] = str(Path(path).resolve())
    return cfg


def resolve_env(value):
    """Если значение вида 'env:VAR_NAME' - вернуть переменную окружения."""
    if isinstance(value, str) and value.startswith("env:"):
        return os.environ.get(value[4:])
    return value