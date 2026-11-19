"""Configurable locations for generated results, separate from source files."""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / '.env')


def output_dir(config=None):
    default = (config or {}).get('output', {}).get('dir', 'outputs')
    path = Path(os.environ.get('FOODSERVICE_OUTPUT_DIR') or default).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def latest_file(kind, config=None):
    names = {'analysis': 'latest_run.txt', 'history': 'latest_presentation.txt'}
    return output_dir(config) / names[kind]
