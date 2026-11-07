"""Task 3, фаза 1: динамика появлений заведений по годам через Wayback.

год первого появления в архиве, не точная дата открытия.
"""
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.data_access.base import DataSource

logger = logging.getLogger(__name__)


def run(source: DataSource, cfg: dict, out_dir: Path) -> None:
    logger.info("Task 3 (phase 1): динамика появлений по годам")
    branches = source.establishments()
    wayback = source.wayback()
    logger.info("Веток: %d, снимков: %d", len(branches), len(wayback))

    # first_seen / last_seen по firm_id
    wayback["dt"] = pd.to_datetime(wayback["timestamp"], format="%Y%m%d%H%M%S", errors="coerce")
    wayback = wayback.dropna(subset=["dt"])
    
    hist = wayback.groupby("firm_id").agg(
        first_seen=("dt", "min"),
        last_seen=("dt", "max"),
        snapshots=("dt", "size"),
    ).reset_index()
    
    hist["first_seen_year"] = hist["first_seen"].dt.year
    logger.info("Уникальных firm_id в wayback: %d", len(hist))

    # Join с branches
    df = branches[["id", "category", "is_chain"]].merge(
        hist, left_on="id", right_on="firm_id", how="inner",
    )
    logger.info("Сматчено с branches: %d", len(df))

    cat_filter = cfg.get("analysis", {}).get("categories")
    if cat_filter:
        df = df[df["category"].isin(cat_filter)]
    logger.info("После фильтра по категориям: %d", len(df))

    if len(df) == 0:
        raise RuntimeError("После join не осталось записей — проверь firm_id ↔ id")

    # Динамика по годам × тип
    by_year = df[df["first_seen_year"] >= 2013].groupby(["first_seen_year", "is_chain"]).size().unstack(fill_value=0)
    by_year = by_year.rename(columns={True: "chain", False: "independent"})
    if "chain" not in by_year.columns: by_year["chain"] = 0
    if "independent" not in by_year.columns: by_year["independent"] = 0
    
    # Сохраняем в CSV
    tables_dir = out_dir / "tables"
    figures_dir = out_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    by_year.to_csv(tables_dir / "task3_first_seen_by_year.csv")
    logger.info("По годам:\n%s", by_year)

    # График
    fig, ax = plt.subplots(figsize=(10, 6))
    by_year.plot(kind="bar", stacked=True, ax=ax, color=["#4C72B0", "#DD8452"])
    ax.set_xlabel("Год первого появления в Wayback")
    ax.set_ylabel("Число заведений")
    ax.set_title("Появление заведений по годам (нижняя граница, Wayback)")
    ax.legend(["Сетевые", "Независимые"])
    fig.tight_layout()
    fig.savefig(figures_dir / "task3_first_seen_by_year.png", dpi=120)
    plt.close(fig)

    logger.info("Task 3: результаты в %s", out_dir)