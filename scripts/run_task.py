"""CLI: python scripts/run_task.py --task 1 [--config config/default.yaml]"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from src.config import load_config
from src.data_access.yt_source import YTSource
from src.tasks import TASKS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=int, required=True)
    parser.add_argument("--config", default="config/default.yaml")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_dotenv()

    cfg = load_config(args.config)

    if args.task not in TASKS:
        sys.exit(f"Задача {args.task} не зарегистрирована. Доступны: {list(TASKS)}")

    source = YTSource(
        cfg["data_source"]["yt"],
        cfg["tables"],
        cfg["analysis"],
    )
    out_dir = Path(cfg["output"]["dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    TASKS[args.task](source, cfg, out_dir)


if __name__ == "__main__":
    main()