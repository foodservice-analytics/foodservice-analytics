"""Task 5: Построение модели выживаемости (Cox Proportional Hazards).

Оцениваем влияние типа владения, категории, района и конкуренции
в радиусе 300 м на риск закрытия заведения.
"""
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lifelines import CoxPHFitter
from lifelines.statistics import proportional_hazard_test

from src.data_access.base import DataSource

logger = logging.getLogger(__name__)


def haversine_distance(lat1, lon1, lat2, lon2):
    """Расстояние между двумя точками в километрах (векторизованное)."""
    R = 6371.0  # радиус Земли в км
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


def add_competitors_features(df: pd.DataFrame, radius_km: float = 0.3) -> pd.DataFrame:
    """Считает число конкурентов в радиусе radius_km для каждого заведения."""
    lats = df["lat"].values
    lons = df["lon"].values
    
    # Матрица расстояний (N x N)
    dist_matrix = haversine_distance(
        lats[:, np.newaxis], lons[:, np.newaxis],
        lats[np.newaxis, :], lons[np.newaxis, :]
    )
    
    # Сколько соседей в радиусе (исключаем само заведение)
    np.fill_diagonal(dist_matrix, np.inf)
    competitors = (dist_matrix <= radius_km).sum(axis=1)
    
    df["competitors_300m"] = competitors
    return df


def run(source: DataSource, cfg: dict, out_dir: Path) -> None:
    logger.info("Task 5: подготовка данных и обучение Cox-модели")
    branches = source.establishments()
    wayback = source.wayback()

    # 1. Собираем историю из wayback
    wayback["dt"] = pd.to_datetime(wayback["timestamp"], format="%Y%m%d%H%M%S", errors="coerce")
    wayback = wayback.dropna(subset=["dt"])
    hist = wayback.groupby("firm_id").agg(
        first_seen=("dt", "min"),
        last_seen=("dt", "max"),
    ).reset_index()

    # 2. Джойним
    df = branches[["id", "category", "is_chain", "district", "lat", "lon", "is_deleted"]].merge(
        hist, left_on="id", right_on="firm_id", how="inner",
    )
    
    # Берем заведения, открытые с 2023 года
    df = df[df["first_seen"] >= pd.Timestamp("2023-01-01")]

    cat_filter = cfg.get("analysis", {}).get("categories")
    if cat_filter:
        df = df[df["category"].isin(cat_filter)]

    logger.info("Строк для модели: %d", len(df))

    # 3. Считаем время жизни и событие
    df["duration"] = (df["last_seen"] - df["first_seen"]).dt.days
    df["duration"] = df["duration"].clip(lower=1)
    df["event"] = df["is_deleted"].astype(int)
    
    # 4. Считаем конкурентов в 300 м
    logger.info("Считаем конкурентов в радиусе 300 м...")
    df = add_competitors_features(df, radius_km=0.3)

    # 5. Подготовка признаков
    # is_chain -> int, category/district -> dummy-переменные
    df["is_chain"] = df["is_chain"].astype(int)
    
    # Берем топ-5 категорий и топ-5 районов, остальные в "other", чтобы не раздувать модель
    top_cats = df["category"].value_counts().head(5).index
    top_dists = df["district"].value_counts().head(5).index
    df["category"] = df["category"].where(df["category"].isin(top_cats), "other_cat")
    df["district"] = df["district"].where(df["district"].isin(top_dists), "other_dist")

    # Создаем dummy-переменные
    df_model = pd.get_dummies(
        df[["duration", "event", "is_chain", "competitors_300m", "category", "district"]],
        columns=["category", "district"], drop_first=True, dtype=int
    )

    # 6. Обучение модели
    if len(df_model) < 30:
        logger.warning("Слишком мало данных для модели (%d строк)", len(df_model))
        return

    cph = CoxPHFitter(penalizer=0.1)  # penalizer для стабильности при малом N
    cph.fit(df_model, duration_col="duration", event_col="event")

    # Сохраняем результаты
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    
    # Саммари модели (Hazard Ratios)
    summary = cph.summary[["coef", "exp(coef)", "p"]]
    summary.columns = ["coef", "hazard_ratio", "p_value"]
    summary.to_csv(tables_dir / "task5_cox_summary.csv")
    logger.info("Результаты Cox-модели:\n%s", summary)

    # 7. График: Forest plot для Hazard Ratios
    # Берем только значимые и не-категориальные
    plot_data = summary.sort_values("hazard_ratio")
    
    fig, ax = plt.subplots(figsize=(10, len(plot_data) * 0.4 + 2))
    y_pos = range(len(plot_data))
    
    ax.errorbar(
        plot_data["hazard_ratio"], y_pos, 
        xerr=[plot_data["hazard_ratio"] - plot_data["hazard_ratio"] * np.exp(-1.96 * cph.standard_errors_), 
              plot_data["hazard_ratio"] * np.exp(1.96 * cph.standard_errors_) - plot_data["hazard_ratio"]],
        fmt="o", color="black", capsize=3
    )
    
    ax.axvline(x=1.0, color="red", linestyle="--", alpha=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(plot_data.index)
    ax.set_xlabel("Hazard Ratio (>1 = риск закрытия выше)")
    ax.set_title("Влияние факторов на риск закрытия (Cox-модель)")
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "task5_cox_forest_plot.png", dpi=120)
    plt.close(fig)

    logger.info("Task 5: результаты в %s", out_dir)
    logger.info("Task 5: модель обучена!")