"""Чтение таблиц из YTsaurus с приведением к стандартной схеме DataSource."""
import logging
import os

import pandas as pd
import yt.wrapper as yt

from src.config import resolve_env
from src.data_access.base import DataSource

logger = logging.getLogger(__name__)


def _extract_primary_category(rubrics) -> str | None:
    """Из массива rubrics берёт name первой рубрики с kind == 'primary'.

    rubrics в YT — это list[dict] или None.
    """
    if not rubrics:
        return None
    for r in rubrics:
        if r.get("kind") == "primary":
            return r.get("name")
    # fallback: первая любая рубрика
    return rubrics[0].get("name")


class YTSource(DataSource):
    def __init__(self, yt_cfg: dict, tables_cfg: dict, analysis_cfg: dict):
        proxy = resolve_env(yt_cfg.get("proxy")) or yt_cfg.get("proxy_default")
        yt.config["proxy"]["url"] = proxy

        token = os.environ.get(yt_cfg.get("token_env", "YT_TOKEN"))
        if not token:
            raise RuntimeError(
                f"Не задан токен YT (env {yt_cfg.get('token_env')}). "
                f"Скопируйте .env.example в .env и заполните."
            )
        yt.config["token"] = token

        yt.config["proxy"]["enable_proxy_discovery"] = False
        yt.config["proxy"]["prefer_https"] = True
        yt.config["read_parallel"]["enable"] = True
        yt.config["read_parallel"]["max_thread_count"] = 8

        self.tables_cfg = tables_cfg
        self.analysis_cfg = analysis_cfg

    def _read_raw(self, spec: dict) -> pd.DataFrame:
        path = spec["path"]
        logger.info("Reading YT table: %s", path)
        rows = list(yt.read_table(path))
        if not rows:
            raise RuntimeError(f"Таблица пустая: {path}")
        return pd.DataFrame(rows)

    def establishments(self) -> pd.DataFrame:
        spec = self.tables_cfg["establishments"]
        df = self._read_raw(spec)

        # Переименование в стандартные имена
        df = df.rename(columns={real: std for real, std in spec["columns"].items()})

        required = {"id", "rubrics", "org_branch_count", "district", "is_deleted"}
        missing = required - set(df.columns)
        if missing:
            raise RuntimeError(
                f"В таблице {spec['path']} нет колонок: {missing}. "
                f"Есть: {list(df.columns)}"
            )

        # id - строка, не трогаем. Явно приводим, на случай если придёт int.
        df["id"] = df["id"].astype(str)

        # Категория из rubrics
        df["category"] = df["rubrics"].apply(_extract_primary_category)

        # is_chain: org_branch_count >= порога
        threshold = int(self.analysis_cfg.get("chain_min_branches", 2))
        df["org_branch_count"] = (
            pd.to_numeric(df["org_branch_count"], errors="coerce").fillna(0).astype(int)
        )
        df["is_chain"] = df["org_branch_count"] >= threshold

        # is_deleted - bool, None -> False
        df["is_deleted"] = df["is_deleted"].fillna(False).astype(bool)

        # Числовые поля
        for col in ("rating", "review_count", "lat", "lon"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def reviews(self) -> pd.DataFrame:
        spec = self.tables_cfg["reviews"]
        logger.info("Reading YT table: %s", spec["path"])
        rows = list(yt.read_table(spec["path"]))
        if not rows:
            raise RuntimeError(f"Таблица пустая: {spec['path']}")
        df = pd.DataFrame(rows)
        df = df.rename(columns={real: std for real, std in spec["columns"].items()})

        required = {"branch_id", "rating", "text"}
        missing = required - set(df.columns)
        if missing:
            raise RuntimeError(
                f"В таблице reviews нет колонок: {missing}. Есть: {list(df.columns)}"
            )

        df["branch_id"] = df["branch_id"].astype(str)
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        if "is_hidden" in df.columns:
            df = df[~df["is_hidden"].fillna(False).astype(bool)]
            
        return df