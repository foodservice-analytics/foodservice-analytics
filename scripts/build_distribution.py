"""Build a source-only ZIP from the current checkout, including uncommitted code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DIRECTORIES = ('src', 'scripts', 'tests', 'config', 'server_sql', 'bi')
ROOT_FILES = {'.gitignore', '.env.example', 'README.md', 'requirements.txt',
              'requirements-dev.txt', 'LICENSE', 'LICENSE.txt'}
SUFFIXES = {'.py', '.sql', '.yaml', '.yml', '.json', '.js', '.sh'}
EXCLUDED = {'.git', '.venv', '__pycache__', 'node_modules', 'vendor', 'runtime', 'private',
            '.local', 'tmp', 'outputs', 'dist', 'build', 'k8s', 'infrastructure'}
SECRET_PATTERNS = (
    re.compile(rb'ytct-[A-Za-z0-9-]{12,}'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}'),
)


def source_files():
    paths = [ROOT / name for name in ROOT_FILES if (ROOT / name).is_file()]
    for directory in DIRECTORIES:
        for path in (ROOT / directory).rglob('*'):
            relative = path.relative_to(ROOT)
            if path.is_symlink() or not path.is_file() or EXCLUDED.intersection(relative.parts):
                continue
            if path.suffix in SUFFIXES or path.name in {'LICENSE', 'LICENSE.txt', '.gitignore'}:
                paths.append(path)
    for path in sorted(set(paths)):
        payload = path.read_bytes()
        if any(pattern.search(payload) for pattern in SECRET_PATTERNS):
            raise RuntimeError(f'Credential material detected in {path.relative_to(ROOT)}')
        yield path, payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/foodservice-analytics.zip')
    args = parser.parse_args()
    files = list(source_files())
    manifest = {str(path.relative_to(ROOT)): hashlib.sha256(payload).hexdigest()
                for path, payload in files}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path, payload in files:
            info = zipfile.ZipInfo.from_file(path, 'foodservice-analytics/' + str(path.relative_to(ROOT)))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload)
        archive.writestr('foodservice-analytics/distribution-manifest.json',
                         json.dumps({'schema_version': 1, 'sha256': manifest}, indent=2))
    print(f'{args.output.resolve()} ({len(files)} source files)')


if __name__ == '__main__':
    main()
