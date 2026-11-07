"""Task 5 (stub): подготовка датасета для survival-модели.

собираем датасет из branches + wayback (first_seen/last_seen)
"""
import logging
from pathlib import Path

import pandas as pd

from src.data_access.base import DataSource

logger = logging.getLogger(__name__)


def run(source: DataSource, cfg: dict, out_dir: Path) -> None:
    logger.info("Task 5 (stub): подготовка датасета выживаемости")
    branches = source.establishments()
    wayback = source.wayback()

    wayback["dt"] = pd.to_datetime(wayback["timestamp"], format="%Y%m%d%H%M%S", errors="coerce")
    wayback = wayback.dropna(subset=["dt"])
    
    hist = wayback.groupby("firm_id").agg(
        first_seen=("dt", "min"),
        last_seen=("dt", "max"),
    ).reset_index()

    # Берем только активные заведения, сматченные с wayback
    df = branches[~branches["is_deleted"]].merge(
        hist, left_on="id", right_on="firm_id", how="inner",
    )
    
    # Только заведения, впервые замеченные с 2023 года (для модели)
    df = df[df["first_seen"] >= pd.Timestamp("2023-01-01")]

    cat_filter = cfg.get("analysis", {}).get("categories")
    if cat_filter:
        df = df[df["category"].isin(cat_filter)]

    dataset = df[["id", "category", "is_chain", "district", "lat", "lon",
                  "first_seen", "last_seen"]].copy()
    dataset["observed_days"] = (dataset["last_seen"] - dataset["first_seen"]).dt.days
    
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(tables_dir / "task5_survival_dataset.csv", index=False)
    
    logger.info("Task 5 (stub): датасет %d строк -> task5_survival_dataset.csv", len(dataset))
    logger.info("Модель Cox/logit — TO DO")