# Анализ заведений общепита Санкт-Петербурга по данным 2ГИС

**Сетевые и независимые заведения: доли, рейтинги, динамика.**

Проект по предмету «Наука о данных и аналитика больших объемов информации». Источники: 2ГИС (основной),
Wayback Machine (архивные снимки 2ГИС), OpenStreetMap (валидация).

---

## Содержание

- [Требования](#требования)
- [Установка](#установка)
- [Настройка доступа к данным](#настройка-доступа-к-данным)
- [Старт](#старт)
- [Структура репозитория](#структура-репозитория)
- [Данные и схема](#данные-и-схема)
- [Задачи анализа](#задачи-анализа)
- [Конфигурация](#конфигурация)
- [CLI](#cli)
- [Формат результатов](#формат-результатов)

---

## Требования

- Python **3.10+**
- Доступ к YTsaurus: прокси `yt-api.xsserver.ru`, токен

---

## Установка

### Windows (native, PowerShell)

```powershell
git clone https://github.com/foodservice-analytics/foodservice-analytics.git
cd foodservice-analytics

py -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
Copy-Item .env.example .env         # и вписать YT_TOKEN (см. ниже)
```

### Linux / macOS / WSL

```bash
git clone https://github.com/foodservice-analytics/foodservice-analytics.git
cd foodservice-analytics

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env                # и вписать YT_TOKEN
```

---

## Настройка доступа к данным

**Прокси для API — `yt-api.xsserver.ru`**

Содержимое `.env`:

```bash
YT_PROXY=yt-api.xsserver.ru
YT_TOKEN=<токен из файла>
```

---

## Старт

```bash
# 1. Один раз: посмотреть реальную схему таблиц (полезно при изменениях в stg)
python scripts/inspect_tables.py

# 2. Запустить задачу
python scripts/run_task.py --task 1
```

Результаты появятся в `outputs/tables/` (CSV) и `outputs/figures/` (PNG).
Папка `outputs/` в git не попадает.

---

## Структура репозитория

```
foodservice-analytics/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example                # шаблон, реальный .env - в .gitignore
├── config/
│   └── default.yaml            # источник данных, маппинг колонок, параметры анализа
├── data/                       # (план) CSV-сэмплы для тестов без доступа к YT
├── src/
│   ├── config.py               # загрузка YAML + разрешение env:VAR
│   ├── data_access/
│   │   ├── base.py             # абстракция DataSource
│   │   └── yt_source.py        # реализация поверх YTsaurus
│   └── tasks/
│       ├── __init__.py         # реестр TASKS
│       ├── task1_shares.py     # доли сетевых/независимых
│       └── task2_ratings.py    # (в работе) сравнение рейтингов и отзывов
├── scripts/
│   ├── inspect_tables.py       # разовая инспекция схемы stg
│   └── run_task.py             # CLI-точка входа
└── outputs/                    # (gitignored) tables/, figures/
```

---

## Данные и схема

Данные лежат в YTsaurus, доступны **только для чтения**:

| Путь | Назначение |
|---|---|
| `//home/spb_food/stg/branches` | Заведения (текущий срез 2ГИС) — **основной источник** |
| `//home/spb_food/stg/branch_ratings` | Рейтинги и число отзывов по каждой ветке |
| `//home/spb_food/stg/reviews` | Отзывы (текст, рейтинг, дата, провайдер) |
| `//home/spb_food/stg/wayback_snapshots` | Архивные снимки 2ГИС (для восстановления динамики) |
| `//home/spb_food/stg/wayback_cdx` | Индекс Wayback CDX (служебное) |
| `//home/spb_food/stg/osm` | OpenStreetMap — для валидации |
| `//home/spb_food/meta/{collection_state,reviews_done_markers}` | Метаданные сбора |
| `//home/spb_food/raw/2gis_{firms,reviews,search}` | Сырые ответы API 2ГИС |

### Ключевые поля `branches`

| Поле | Тип | Комментарий |
|---|---|---|
| `id` | str | ID ветки в 2ГИС (не int!) |
| `org_id` | str | ID организации; общий для всех веток сети |
| `org_branch_count` | int | Число филиалов организации — на нём строится `is_chain` |
| `rubrics` | list[dict] | Рубрики; основная — где `kind == "primary"` |
| `district` | str | Район (`"Адмиралтейский район"` и т. д.) |
| `city` | str | Город |
| `lat`, `lon` | float | Координаты |
| `rating`, `review_count` | float/int | Рейтинг и число отзывов ветки |
| `is_deleted` | bool | True — заведение закрыто |
| `deleted_at` | str/null | Дата закрытия (часто `null` даже у `is_deleted=True`) |
| `created_at` | null | **Всегда `null`** — дату открытия из 2ГИС получить нельзя |

### Как определяется «сетевое» и «независимое»

- `is_chain = (org_branch_count >= chain_min_branches)` — порог задаётся в `config/default.yaml`
  (`analysis.chain_min_branches`, по умолчанию **2**).
- `category` — из `rubrics`, берётся `name` первой рубрики с `kind == "primary"`.
- `closed` = `is_deleted == True`. См. [ограничения] - флаг
  ловит только часть реальных закрытий.

---

## Задачи анализа

| № | Задача | Статус | Файл |
|---|---|---|---|
| 1 | Доля сетевых и независимых по категориям и районам (снимок «сейчас»). **Фаза 2** — динамика с 2018 через `wayback_snapshots` | фаза 1 готова<br> фаза 2 запланирована | `task1_shares.py` |
| 2 | Сравнение рейтингов и числа отзывов сетевых/независимых внутри категорий (boxplot + Mann-Whitney U) | в работе | `task2_ratings.py` |
| 3 | Динамика открытий (с 2018) и закрытий (2023–2026) | заблокировано: нужен wayback-парсер | — |
| 4 | Причины негативных оценок в отзывах (сетевые vs независимые) | запланировано | — |
| 5 | Модель выживаемости (Cox/logit): категория, тип владения, район, конкуренты в 300 м | заблокировано: нужны даты открытия/закрытия из wayback | — |

**task3 и task5:** в `branches` нет `opened_date` и надёжного
`closed_date`. `created_at` везде `null`, `is_deleted` покрывает лишь ~5% реальных
закрытий. Даты восстанавливаются **только** из `wayback_snapshots` (first-seen /
last-seen по `firm_id`).

---

## Конфигурация

Всё, что может меняться между запусками, — в `config/default.yaml`:

```yaml
data_source:
  type: yt
  yt:
    proxy: "env:YT_PROXY"             # "env:VAR" - берётся из окружения
    proxy_default: "yt-api.xsserver.ru"
    token_env: "YT_TOKEN"

tables:
  establishments:
    path: "//home/spb_food/stg/branches"
    columns:                          # реальное_имя: стандартное_имя
      id: id
      ...

analysis:
  date_to: "2026-10-31"
  chain_min_branches: 2
  categories:
    - "Рестораны"
    - "Кафе"
    - "Кофейни"
    - "Быстрое питание"
    - "Пекарни"

output:
  dir: "outputs"
```

Чтобы поменять порог «сетевое = от 3 филиалов» - правится одна строка `chain_min_branches`.
Чтобы временно отключить фильтр по категориям - убрать блок `categories`.

---

## CLI

```bash
python scripts/run_task.py --task 1                    # дефолтный конфиг
python scripts/run_task.py --task 2 --config config/default.yaml
```

При запуске:
- читается `.env`,
- поднимается `YTSource` с настройками из `config/default.yaml`,
- вызывается `TASKS[task](source, cfg, out_dir)`,
- результаты складываются в `outputs/`.

---

## Формат результатов

Для каждой задачи:
- `outputs/tables/taskN_<name>.csv` - таблица результата;
- `outputs/figures/taskN_<name>.png` - график (dpi=120, Agg-backend, работает без GUI).

Имена файлов фиксированы, чтобы их можно было автоматически подхватывать при сборке
статьи и презентации.