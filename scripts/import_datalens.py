"""Import/verify the dashboard over the existing DataLens HTTPS API (OSS 2.9)."""
import argparse
import getpass
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.paths import PROJECT_ROOT, latest_file
from src.datalens import DataLensHTTP, WorkbookImporter, check_spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=os.getenv('DATALENS_URL'))
    parser.add_argument('--login', default=os.getenv('DATALENS_LOGIN'))
    parser.add_argument('--workbook-id')
    parser.add_argument('--connection-id')
    parser.add_argument('--title', default='Общепит Санкт-Петербурга')
    parser.add_argument('--analysis-dir', type=Path)
    parser.add_argument('--history-dir', type=Path)
    parser.add_argument('--state-file', type=Path, default=Path(os.getenv('DATALENS_STATE_FILE', '.local/datalens-import.json')))
    parser.add_argument('--update', action='store_true', help='Update objects from this state, preserving IDs and creating backups')
    parser.add_argument('--verify', action='store_true', help='Only read and verify existing objects')
    parser.add_argument('--offline', action='store_true', help='Only validate the portable specification')
    parser.add_argument('--dry-run', action='store_true', help='Show planned roots/objects without contacting DataLens')
    args = parser.parse_args()
    spec = json.loads((PROJECT_ROOT/'bi/datalens/workbook/dashboard_spec.json').read_text())
    counts = check_spec(spec)
    if args.offline:
        print(json.dumps({'status': 'passed', **counts})); return
    saved = json.loads(args.state_file.read_text()) if args.state_file.exists() else {}
    folders = []
    for supplied, kind in [(args.analysis_dir, 'analysis'), (args.history_dir, 'history')]:
        if args.verify and supplied is None and saved.get(kind + '_root'):
            folders.append(saved[kind + '_root']); continue
        pointer = latest_file(kind)
        if supplied is None and not pointer.exists():
            parser.error(f'Run the analysis or provide --{kind if kind == "analysis" else "history"}-dir')
        folder = supplied or Path(pointer.read_text().strip())
        manifest = json.loads((folder/'manifest.json').read_text())
        if manifest.get('status') != 'complete':
            parser.error('Only completed runs may be imported')
        folders.append(manifest.get('root') or '//home/team/foodservice_analytics/'+manifest['run_id'])
    if args.dry_run:
        print(json.dumps({**counts, 'analysis_root': folders[0], 'history_root': folders[1]}, indent=2)); return
    if not args.url or not args.login:
        parser.error('Set DATALENS_URL and DATALENS_LOGIN')
    password = os.getenv('DATALENS_PASSWORD')
    if not password:
        if not sys.stdin.isatty(): parser.error('Set DATALENS_PASSWORD for non-interactive execution')
        password = getpass.getpass('DataLens password: ')
    api = DataLensHTTP(args.url, args.login, password)
    importer = WorkbookImporter(api, spec, args.state_file, *folders)
    if args.verify:
        print(json.dumps(importer.verify())); return
    importer.bind(args.title, args.workbook_id, args.connection_id, os.getenv('YT_TOKEN'), os.getenv('YT_PROXY', 'yt-api.xsserver.ru'))
    print(importer.import_all(args.update))
    print(json.dumps(importer.verify()))


if __name__ == '__main__':
    main()
