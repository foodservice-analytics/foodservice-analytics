"""Абстракция источника данных.

Все задачи (task1..task5) получают объект DataSource и не знают,
откуда именно пришли данные — из YTsaurus или из CSV-примеров данных.

В исходной таблице //home/spb_food/stg/branches
Нет полей opened_date и closed_date. Они восстанавливаются позже из
wayback_snapshots. Поэтому контракт ниже не содержит их — но содержит
is_deleted (флаг «закрыто сейчас») и org_branch_count (для is_chain).
"""
from abc import ABC, abstractmethod

import pandas as pd


class DataSource(ABC):
    """Стандартизированный доступ к данным проекта."""

    @abstractmethod
    def establishments(self) -> pd.DataFrame:
        """Заведения общепита (снимок «сейчас»).

        Колонки:
          id                 — str, идентификатор заведения в 2ГИС
          name               — str, название
          category           — str, основная рубрика ('Рестораны', 'Кафе', ...)
                                None, если рубрик нет
          is_chain           — bool, True если org_branch_count >= порога
          district           — str, район города ('Адмиралтейский район', ...)
          city               — str, город
          lat, lon           — float, координаты
          rating             — float | None, средний рейтинг (ветка)
          review_count       — int | None, число отзывов (ветка)
          is_deleted         — bool, True если заведение закрыто
          deleted_at         — str | None, дата закрытия (если есть)
          org_branch_count   — int, число филиалов организации (для аудита)
        """
        
    @abstractmethod
    def reviews(self) -> pd.DataFrame:
        """Отзывы о заведениях.

        Колонки:
          branch_id     — str, ID ветки (= branches.id)
          review_id     — str, ID отзыва
          date_created  — str, ISO-дата создания
          rating        — int, оценка 1..5
          text          — str | None, текст отзыва
          provider      — str, '2gis' | 'flamp' | ...
          is_hidden     — bool, скрыт ли отзыв модерацией
        """

    @abstractmethod
    def wayback(self) -> pd.DataFrame:
        """Снимки Wayback Machine для 2ГИС."""
        ...