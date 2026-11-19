# Анализ общепита Санкт-Петербурга

[Дашборд в DataLens](https://datalens.xsserver.ru/t60k6u9mvycsc).

## Входные данные

Исходные таблицы находятся в YTsaurus: `//home/spb_food/stg`. Пути к таблицам и параметры анализа заданы в `config/server.yaml`.

В `.env` должны быть заполнены `YT_PROXY` и `YT_TOKEN`. Токен используется для чтения исходных таблиц и записи результатов в `//home/team/foodservice_analytics`.

## Выходные данные

Расчёты выполняются в CHYT и серверных заданиях MapReduce. Результаты записываются в отдельный каталог YTsaurus для каждого запуска.

Для загрузки в DataLens в `.env` должны быть заполнены `DATALENS_URL`, `DATALENS_LOGIN` и `DATALENS_PASSWORD`. Скрипт импорта создаёт книгу, подключение CHYT и дашборд через HTTP API DataLens OSS 2.9.

## Запуск

Python 3.15.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

После заполнения `.env`:

```bash
python scripts/run_dashboard_pipeline.py
python scripts/import_datalens.py
```