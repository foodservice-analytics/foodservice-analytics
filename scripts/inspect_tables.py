"""Разовый скрипт: посмотреть, какие таблицы есть в stg и какие в них колонки.

Запуск:  python scripts/inspect_tables.py
Затем обновите config/default.yaml под реальные имена колонок
(особенно tables.establishments.columns).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
import yt.wrapper as yt

load_dotenv()

proxy = os.environ.get("YT_PROXY", "yt-api.xsserver.ru")
token = os.environ.get("YT_TOKEN")
if not token:
    sys.exit("YT_TOKEN не задан. Заполните .env")

yt.config["proxy"]["url"] = proxy
yt.config["token"] = token
yt.config["proxy"]["enable_proxy_discovery"] = False
yt.config["proxy"]["prefer_https"] = True

BASE = "//home/spb_food/stg"

print(f"Прокси: {proxy}")
print(f"Таблицы в {BASE}:")
for t in yt.list(BASE):
    print(f"\n=== {t} ===")
    path = f"{BASE}/{t}"
    try:
        # Берём первые 3 строки, чтобы понять схему
        rows = list(yt.read_table(path, format=yt.JsonFormat(attributes={"encode_utf8": False})))
        for row in rows[:3]:
            print(row)
    except Exception as e:
        print(f"  ошибка чтения: {e}")

# Заодно посмотрим, что в meta и raw
for folder in ("meta", "raw"):
    path = f"//home/spb_food/{folder}"
    try:
        print(f"\nТаблицы в {path}: {yt.list(path)}")
    except Exception as e:
        print(f"\n{path}: {e}")