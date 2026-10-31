"""Task 1, фаза 1: доли сетевых и независимых заведений на снимке «сейчас»
по категориям и районам.

Фаза 2 (динамика с 2018) — отдельно, через wayback_snapshots. Здесь её нет.
"""
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.data_access.base import DataSource

logger = logging.getLogger(__name__)


def _share_table(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Доли chain/independent по group_col на снимке."""
    counts = df.groupby([group_col, "is_chain"]).size().unstack(fill_value=0)
    for val in (True, False):
        if val not in counts.columns:
            counts[val] = 0
    counts = counts.rename(columns={True: "chain", False: "independent"})
    counts = counts[["chain", "independent"]]
    total = counts.sum(axis=1)
    shares = counts.div(total.where(total > 0, 1), axis=0)
    shares["total"] = total
    return shares.reset_index().sort_values("total", ascending=False)


def run(source: DataSource, cfg: dict, out_dir: Path) -> None:
    logger.info("Task 1 (phase 1): доли сетевых/независимых, снимок «сейчас»")

    df = source.establishments()
    logger.info("Всего записей: %d", len(df))

    # Оставляем только активные (не закрытые)
    active = df[~df["is_deleted"]].copy()
    logger.info("Активных: %d (закрытых: %d)", len(active), len(df) - len(active))

    # Опционально: только те категории, что в конфиге (если список задан)
    cat_filter = cfg.get("analysis", {}).get("categories")
    if cat_filter:
        active = active[active["category"].isin(cat_filter)]
        logger.info("После фильтра по категориям: %d", len(active))

    shares_cat = _share_table(active.dropna(subset=["category"]), "category")
    shares_dist = _share_table(active.dropna(subset=["district"]), "district")

    tables_dir = out_dir / "tables"
    figures_dir = out_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    shares_cat.to_csv(tables_dir / "task1_shares_by_category.csv", index=False)
    shares_dist.to_csv(tables_dir / "task1_shares_by_district.csv", index=False)

    # График: доли по категориям
    fig, ax = plt.subplots(figsize=(10, 6))
    shares_cat.set_index("category")[["chain", "independent"]].plot(
        kind="bar", stacked=True, ax=ax, color=["#4C72B0", "#DD8452"],
    )
    ax.set_ylabel("Доля")
    ax.set_xlabel("Категория")
    ax.set_title("Доля сетевых и независимых заведений по категориям (снимок 2026-10)")
    ax.legend(["Сетевые", "Независимые"])
    fig.tight_layout()
    fig.savefig(figures_dir / "task1_shares_by_category.png", dpi=120)
    plt.close(fig)

    # График: топ-10 районов по total
    top_dist = shares_dist.head(10).set_index("district")
    fig, ax = plt.subplots(figsize=(10, 6))
    top_dist[["chain", "independent"]].plot(
        kind="barh", stacked=True, ax=ax, color=["#4C72B0", "#DD8452"],
    )
    ax.set_xlabel("Доля")
    ax.set_ylabel("Район")
    ax.set_title("Доля сетевых и независимых по районам (топ-10)")
    ax.legend(["Сетевые", "Независимые"])
    fig.tight_layout()
    fig.savefig(figures_dir / "task1_shares_by_district_top10.png", dpi=120)
    plt.close(fig)

    logger.info("Task 1: результаты в %s", out_dir)
    logger.info("Категорий: %d, районов: %d", len(shares_cat), len(shares_dist))