"""Task 4: причины негативных оценок в отзывах — сетевые vs независимые.

Подход без NLP-моделей: словари ключевых слов по темам.
"""
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.data_access.base import DataSource

logger = logging.getLogger(__name__)

# Темы и подстроки-триггеры
TOPIC_KEYWORDS = {
    "сервис":    ["обслуживан", "официант", "персонал", "ждать", "долго", "медленн",
                  "хамств", "груб", "невнимательн", "очередь"],
    "еда":       ["вкусн", "невкусн", "еда", "блюдо", "кухн", "свеж", "несвеж",
                  "порци", "сыр", "мясо", "рыб"],
    "цена":      ["дорого", "цена", "чек", "переплат", "стоимост", "дешев", "наценк"],
    "чистота":   ["грязн", "чист", "туалет", "пыль", "запах", "санитар"],
    "атмосфера": ["шумн", "атмосфер", "интерьер", "музык", "тесно", "душн", "уютн"],
}

def _match_topics(text: str) -> set[str]:
    if not isinstance(text, str):
        return set()
    t = text.lower()
    return {topic for topic, keys in TOPIC_KEYWORDS.items() if any(k in t for k in keys)}


def run(source: DataSource, cfg: dict, out_dir: Path) -> None:
    logger.info("Task 4: причины негативных оценок")
    branches = source.establishments()
    reviews = source.reviews()
    logger.info("Веток: %d, отзывов: %d", len(branches), len(reviews))

    # Оставляем только активные заведения и только наши категории
    branches = branches[~branches["is_deleted"]].copy()
    cat_filter = cfg.get("analysis", {}).get("categories")
    if cat_filter:
        branches = branches[branches["category"].isin(cat_filter)]
    logger.info("Веток после фильтра: %d", len(branches))

    # Join отзывов к веткам
    df = reviews.merge(
        branches[["id", "category", "is_chain"]],
        left_on="branch_id", right_on="id", how="inner",
    )
    logger.info("Отзывов после join: %d", len(df))

    if len(df) == 0:
        raise RuntimeError("После join не осталось отзывов — проверь branch_id ↔ id")

    # Классификация
    df["is_negative"] = df["rating"].fillna(0) <= 2
    df["is_positive"] = df["rating"].fillna(0) >= 4

    # 1. Распределение оценок по типу
    dist = df.groupby(["is_chain", "rating"]).size().unstack(fill_value=0)
    dist = dist.rename(index={True: "chain", False: "independent"})
    dist.to_csv(out_dir / "tables" / "task4_rating_distribution.csv")

    # 2. Доля негативных отзывов
    neg_share = df.groupby("is_chain").agg(
        total=("review_id", "size"),
        negative=("is_negative", "sum"),
    )
    neg_share["negative_share"] = neg_share["negative"] / neg_share["total"]
    neg_share = neg_share.rename(index={True: "chain", False: "independent"})
    neg_share.to_csv(out_dir / "tables" / "task4_negative_share.csv")
    logger.info("Доля негатива:\n%s", neg_share)

    # 3. Темы в негативных отзывах
    neg = df[df["is_negative"]].copy()
    neg["topics"] = neg["text"].apply(_match_topics)

    exploded = neg.explode("topics").dropna(subset=["topics"])
    topic_counts = exploded.groupby(["is_chain", "topics"]).size().unstack(fill_value=0)
    topic_counts = topic_counts.rename(index={True: "chain", False: "independent"})

    total_neg = neg.groupby("is_chain").size().rename({True: "chain", False: "independent"})
    topic_shares = topic_counts.div(total_neg, axis=0)
    topic_shares.to_csv(out_dir / "tables" / "task4_topic_shares_in_negative.csv")
    logger.info("Доли тем в негативе:\n%s", topic_shares)

    # 4. Графики
    figures_dir = out_dir / "figures"

    # Распределение оценок
    fig, ax = plt.subplots(figsize=(8, 5))
    dist.plot(kind="bar", ax=ax, color=["#d62728", "#ff7f0e", "#ffdd57", "#9ccc65", "#2e7d32"])
    ax.set_xlabel("Тип заведения")
    ax.set_ylabel("Число отзывов")
    ax.set_title("Распределение оценок: сетевые vs независимые")
    ax.legend(title="Оценка", loc="upper right")
    fig.tight_layout()
    fig.savefig(figures_dir / "task4_rating_distribution.png", dpi=120)
    plt.close(fig)

    # Темы в негативе
    fig, ax = plt.subplots(figsize=(10, 6))
    topic_shares.T.plot(kind="barh", ax=ax, color=["#4C72B0", "#DD8452"])
    ax.set_xlabel("Доля негативных отзывов, упоминающих тему")
    ax.set_ylabel("Тема")
    ax.set_title("Причины негатива: сетевые vs независимые")
    ax.legend(["Сетевые", "Независимые"])
    fig.tight_layout()
    fig.savefig(figures_dir / "task4_topics_in_negative.png", dpi=120)
    plt.close(fig)

    logger.info("Task 4: результаты в %s", out_dir)