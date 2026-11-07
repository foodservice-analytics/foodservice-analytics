"""Task 2: сравнение рейтингов и числа отзывов сетевых и независимых
внутри каждой категории.
"""
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import mannwhitneyu

from src.data_access.base import DataSource

logger = logging.getLogger(__name__)


def _group_stats(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows = []
    for cat in sorted(df["category"].dropna().unique()):
        sub = df[df["category"] == cat]
        for is_chain, label in [(True, "chain"), (False, "independent")]:
            s = sub[sub["is_chain"] == is_chain][metric].dropna()
            if len(s) == 0:
                continue
            rows.append({
                "category": cat,
                "type": label,
                "metric": metric,
                "n": len(s),
                "mean": s.mean(),
                "median": s.median(),
                "q25": s.quantile(0.25),
                "q75": s.quantile(0.75),
            })
    return pd.DataFrame(rows)


def _mannwhitney(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows = []
    for cat in sorted(df["category"].dropna().unique()):
        sub = df[df["category"] == cat]
        chain = sub[sub["is_chain"]][metric].dropna()
        indep = sub[~sub["is_chain"]][metric].dropna()
        if len(chain) < 5 or len(indep) < 5:
            continue
        stat, p = mannwhitneyu(chain, indep, alternative="two-sided")
        rows.append({
            "category": cat,
            "metric": metric,
            "n_chain": len(chain),
            "n_independent": len(indep),
            "u_stat": stat,
            "p_value": p,
            "significant_at_0.05": p < 0.05,
        })
    return pd.DataFrame(rows)


def _boxplot(df: pd.DataFrame, metric: str, out_path: Path, ylabel: str, log_scale: bool = False) -> None:
    cats = sorted(df["category"].dropna().unique())
    fig, ax = plt.subplots(figsize=(max(10, 1.6 * len(cats)), 6))

    data_chain = [df[(df["category"] == c) & df["is_chain"]][metric].dropna() for c in cats]
    data_indep = [df[(df["category"] == c) & ~df["is_chain"]][metric].dropna() for c in cats]

    positions_chain = [i - 0.2 for i in range(len(cats))]
    positions_indep = [i + 0.2 for i in range(len(cats))]

    bp1 = ax.boxplot(data_chain, positions=positions_chain, widths=0.35, patch_artist=True)
    bp2 = ax.boxplot(data_indep, positions=positions_indep, widths=0.35, patch_artist=True)
    for bp, color in [(bp1, "#4C72B0"), (bp2, "#DD8452")]:
        for patch in bp["boxes"]:
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, rotation=15)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{ylabel}: сетевые vs независимые по категориям")

    if log_scale:
        ax.set_yscale("log")

    ax.legend([bp1["boxes"][0], bp2["boxes"][0]], ["Сетевые", "Независимые"])
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def run(source: DataSource, cfg: dict, out_dir: Path) -> None:
    logger.info("Task 2: сравнение рейтингов и отзывов")

    df = source.establishments()
    active = df[~df["is_deleted"]].copy()

    cat_filter = cfg.get("analysis", {}).get("categories")
    if cat_filter:
        active = active[active["category"].isin(cat_filter)]

    rated = active[active["rating"] > 0].dropna(subset=["category", "rating"]).copy()
    logger.info("Заведений с рейтингом: %d", len(rated))

    tables_dir = out_dir / "tables"
    figures_dir = out_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    rating_stats = _group_stats(rated, "rating")
    rating_stats.to_csv(tables_dir / "task2_rating_stats.csv", index=False)

    with_reviews = active.dropna(subset=["category", "review_count"]).copy()
    review_stats = _group_stats(with_reviews, "review_count")
    review_stats.to_csv(tables_dir / "task2_review_count_stats.csv", index=False)

    mw_rating = _mannwhitney(rated, "rating")
    mw_rating.to_csv(tables_dir / "task2_mannwhitney_rating.csv", index=False)

    mw_reviews = _mannwhitney(with_reviews, "review_count")
    mw_reviews.to_csv(tables_dir / "task2_mannwhitney_review_count.csv", index=False)

    _boxplot(rated, "rating", figures_dir / "task2_rating_boxplot.png", "Рейтинг")
    _boxplot(with_reviews, "review_count", figures_dir / "task2_review_count_boxplot.png", "Число отзывов", log_scale=True)

    logger.info("Task 2: результаты в %s", out_dir)
    if len(mw_rating) > 0:
        n_sig = int(mw_rating["significant_at_0.05"].sum())
        logger.info("Mann-Whitney rating — значимых (p<0.05): %d из %d", n_sig, len(mw_rating))
    if len(mw_reviews) > 0:
        n_sig = int(mw_reviews["significant_at_0.05"].sum())
        logger.info("Mann-Whitney review_count — значимых (p<0.05): %d из %d", n_sig, len(mw_reviews))