"""Local-only inventory and source snapshot. Never stages, commits or deploys.

Snapshots intentionally omit credentials, databases, dependencies, generated output
and other worktrees. They are NOT a backup of production or the entire computer.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', '.agents', '.claude', '.codex', '.codex-remote-attachments',
             '.vercel', '.pytest_cache', '__pycache__', 'venv', 'node_modules',
             'dist', 'output', 'test-results', 'playwright-report', 'logos',
             'backups', 'tmp', 'pruebas', 'pruebas qwen', 'Smart_PSE',
             '_push_main_sync', '_push_quote_footer_main', '_release_guides_prod'}
SOURCE_ROOTS = ('backend', 'frontend', 'docs', 'contracts', 'scripts', 'supabase', '.impeccable', 'logo')
PRIVATE_EXTENSIONS = {'.pem', '.key', '.pfx', '.p12', '.db', '.sqlite', '.sqlite3', '.log', '.dump', '.backup'}


def git(*args, root=ROOT):
    return subprocess.check_output(['git', '-C', str(root), *args])


def digest(data):
    return hashlib.sha256(data).hexdigest()


def permitted(path):
    parts = path.parts
    name = path.name.lower()
    if any(part in SKIP_DIRS for part in parts):
        return False
    if name.startswith('.env') and not name.endswith('.example'):
        return False
    return path.suffix.lower() not in PRIVATE_EXTENSIONS and name not in {'auth.json', 'credentials.json', 'storage-state.json'} and not name.endswith('.pyc')


def category(name):
    if name.startswith('backend/alembic/'):
        return 'migraciones'
    if name.startswith(('backend/test_', 'frontend/e2e/')) or '.test.' in name:
        return 'pruebas'
    if name.startswith('backend/'):
        return 'backend'
    if name.startswith('frontend/'):
        return 'frontend'
    if name.startswith(('docs/', 'contracts/', 'scripts/')):
        return name.split('/')[0]
    return 'configuracion_y_referencias'


def candidates():
    tracked = {name for name in git('ls-files', '-z').decode('utf-8').split('\0') if name}
    paths = {name for name in tracked if permitted(Path(name))}
    for name in SOURCE_ROOTS:
        base = ROOT / name
        if not base.exists():
            continue
        for current, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (Path(current) / d).is_symlink())
            for filename in files:
                path = Path(current) / filename
                rel = path.relative_to(ROOT)
                if permitted(rel) and not path.is_symlink() and not (path.stat().st_file_attributes & 0x400 if hasattr(path.stat(), 'st_file_attributes') else False):
                    paths.add(rel.as_posix())
    for path in ROOT.iterdir():
        if path.is_file() and not path.is_symlink() and permitted(Path(path.name)) and path.suffix.lower() in {'.md', '.py', '.json', '.ini', '.toml', '.bat', '.html'}:
            paths.add(path.name)
    return sorted(paths), tracked


def release_state():
    spec = importlib.util.spec_from_file_location('release_guard', ROOT / 'scripts/release_guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    return guard.manifest(ROOT)


def verify(destination):
    report = json.loads((destination / 'inventory.json').read_text(encoding='utf-8'))
    archive = destination / 'sources.zip'
    if digest(archive.read_bytes()) != report['archive_sha256']:
        raise ValueError('La huella del respaldo no coincide')
    with zipfile.ZipFile(archive) as source:
        for item in report['files']:
            if item['exists'] and digest(source.read('current/' + item['path'])) != item['sha256']:
                raise ValueError('Contenido incorrecto: ' + item['path'])
        for item in report['deleted_head_copies']:
            if digest(source.read('deleted-at-head/' + item['path'])) != item['sha256']:
                raise ValueError('Copia histórica incorrecta: ' + item['path'])
        if source.testzip():
            raise ValueError('ZIP dañado')
    print(json.dumps({'verified': True, 'files': sum(i['exists'] for i in report['files']),
                      'deleted_head_copies': len(report['deleted_head_copies']),
                      'release_sha256': report['release_sha256']}, indent=2))


def snapshot(destination, expected_release):
    destination = destination.resolve()
    backup_root = (ROOT / 'backups').resolve()
    if not destination.is_relative_to(backup_root) or destination == backup_root or destination.exists():
        raise ValueError('Usar un directorio NUEVO dentro de backups/')
    release_before = release_state()
    if release_before['content_sha256'] != expected_release:
        raise ValueError('La aplicación difiere de la entrega esperada: detener y revisar')
    status_before = git('status', '--porcelain=v1', '-z', '--untracked-files=normal')
    index_before = git('diff', '--cached', '--binary')
    paths, tracked = candidates()
    destination.mkdir(parents=True)
    report = {'created_utc': datetime.now(timezone.utc).isoformat(),
              'base_revision': git('rev-parse', 'HEAD').decode().strip(),
              'branch': git('branch', '--show-current').decode().strip(),
              'release_sha256': expected_release, 'files': [], 'deleted_head_copies': [],
              'excluded_directories': sorted(SKIP_DIRS),
              'scope': 'main workspace source only; not credentials, databases, auxiliary worktrees or production'}
    with zipfile.ZipFile(destination / 'sources.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in paths:
            path = ROOT / name
            if not path.resolve().is_relative_to(ROOT) or path.is_symlink():
                continue
            exists = path.is_file()
            item = {'path': name, 'category': category(name), 'tracked': name in tracked, 'exists': exists}
            if exists:
                data = path.read_bytes()
                item.update(size=len(data), sha256=digest(data))
                archive.writestr('current/' + name, data)
            elif name in tracked:
                try:
                    data = git('show', 'HEAD:' + name)
                    archive.writestr('deleted-at-head/' + name, data)
                    report['deleted_head_copies'].append({'path': name, 'sha256': digest(data)})
                except subprocess.CalledProcessError:
                    raise ValueError('No se pudo preservar el archivo eliminado: ' + name)
            report['files'].append(item)
        archive.writestr('metadata/git-status-before.z', status_before)
        archive.writestr('metadata/index-before.patch', index_before)
        archive.writestr('metadata/worktrees.txt', git('worktree', 'list', '--porcelain'))
        archive.writestr('metadata/refs.txt', git('for-each-ref', '--format=%(objectname) %(refname)'))
        archive.writestr('metadata/release-manifest.json', json.dumps(release_before, indent=2))
        for rel in ('_release_guides_prod', '_push_main_sync', '_push_quote_footer_main'):
            archive.writestr('metadata/' + rel + '-status.z', git('status', '--porcelain=v1', '-z', root=ROOT / rel))
    report['archive_sha256'] = digest((destination / 'sources.zip').read_bytes())
    report['counts_by_category'] = dict(Counter(i['category'] for i in report['files']))
    report['existing_untracked'] = sum(i['exists'] and not i['tracked'] for i in report['files'])
    # Verify source and index did not change during the snapshot, even outside the release subset.
    for item in report['files']:
        path = ROOT / item['path']
        if path.is_file() != item['exists'] or (item['exists'] and digest(path.read_bytes()) != item['sha256']):
            raise ValueError('La fuente cambió durante el respaldo: ' + item['path'])
    if git('diff', '--cached', '--binary') != index_before or git('status', '--porcelain=v1', '-z', '--untracked-files=normal') != status_before:
        raise ValueError('Git cambió durante el respaldo; no consolidar')
    if release_state()['content_sha256'] != expected_release:
        raise ValueError('Cambió la huella de aplicación; detener')
    (destination / 'inventory.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    verify(destination)
    print(json.dumps({'counts_by_category': report['counts_by_category'], 'existing_untracked': report['existing_untracked'],
                      'archive_bytes': (destination / 'sources.zip').stat().st_size}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['snapshot', 'verify'])
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--expected-release')
    args = parser.parse_args()
    if args.command == 'verify':
        verify(args.destination)
    else:
        snapshot(args.destination, args.expected_release)
