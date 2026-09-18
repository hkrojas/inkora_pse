"""Inkora: validate the canonical source, freeze and verify one delivery.

Never deploy the working tree or a historical release directory directly.
This tool does not deploy, modify a database, or read environment secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'venv', 'node_modules', '__pycache__', '.git', '.pytest_cache', 'dist', 'output', 'logos', 'pruebas', 'pruebas qwen', 'e2e'}
BACKEND_DIRS = {'crud', 'models', 'routers', 'schemas', 'services', 'alembic'}
CONFIG_FILES = ('Dockerfile', '.dockerignore', 'railway.json', 'frontend/package.json',
                'frontend/package-lock.json', 'frontend/index.html', 'frontend/vite.config.js',
                'frontend/tailwind.config.js', 'frontend/postcss.config.js', 'frontend/vercel.json',
                'backend/requirements.txt', 'backend/alembic.ini')
FEATURES = {
    'frontend/src/components/documents/FiscalDocumentActions.jsx': ['retry_artifacts', 'retry_emission', 'ActionMenu', 'useFiscalTracking', 'credit_note', 'debit_note'],
    'frontend/src/pages/CotizacionesPage.jsx': ['ActionMenu', 'FiscalDocumentActions', 'buildFiscalListQuery'],
    'frontend/src/components/ui/ActionMenu.jsx': ['Escape', 'aria-expanded', 'createPortal'],
    'frontend/src/hooks/useFiscalTracking.js': ['emission-jobs', 'AbortController', 'background: true'],
    'frontend/src/pages/ConfiguracionPage.jsx': ['PaymentQrCropper', 'communicationTemplates'],
    'frontend/src/pages/SuperadminPage.jsx': ['viewingContingencyOf', 'accessRequests'],
    'frontend/src/pages/InventarioPage.jsx': ['submitBulk', 'openWarehouseEdit'],
    'frontend/src/App.jsx': ['GuiaNuevaPage', 'AccessRequestPage', 'LandingPage'],
    'frontend/src/lib/utils/documents.js': ['tenant?.fiscal_invoice_series', 'tenant?.fiscal_boleta_series'],
    'backend/services/document_actions_service.py': ['pending_confirmation', '1033'],
}
HASH_MODE_RAW_V1 = 'raw-v1'
HASH_MODE_CANONICAL_TEXT_V1 = 'canonical-text-v1'
CURRENT_HASH_MODE = HASH_MODE_CANONICAL_TEXT_V1
SUPPORTED_HASH_MODES = {HASH_MODE_RAW_V1, HASH_MODE_CANONICAL_TEXT_V1}


def _canonical_content(data, *, hash_mode):
    if hash_mode == HASH_MODE_RAW_V1:
        return data
    if hash_mode != HASH_MODE_CANONICAL_TEXT_V1:
        raise ValueError(f'Modo de huella no soportado: {hash_mode}')
    if b'\x00' in data:
        return data
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return data
    return text.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')


def digest(path, *, hash_mode=CURRENT_HASH_MODE):
    content = _canonical_content(path.read_bytes(), hash_mode=hash_mode)
    return hashlib.sha256(content).hexdigest()


def manifest_digest(files, *, hash_mode):
    payload = files if hash_mode == HASH_MODE_RAW_V1 else {
        'hash_mode': hash_mode,
        'files': files,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def source_files(root, *, hash_mode=CURRENT_HASH_MODE):
    files = set()
    for rel in CONFIG_FILES:
        path = root / rel
        if path.is_file():
            files.add(rel)
    for base in ('backend', 'frontend/src', 'frontend/static'):
        for path in (root / base).rglob('*'):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(root)
            if any(part in EXCLUDED or part.startswith('.') for part in rel.parts):
                continue
            if base == 'backend':
                if path.suffix != '.py' or path.name.startswith(('test_', 'conftest', 'audit_', 'preflight_')):
                    continue
                if len(rel.parts) > 2 and rel.parts[1] not in BACKEND_DIRS:
                    continue
            if path.suffix.lower() in {'.pem', '.key', '.pfx', '.p12', '.db', '.sqlite', '.log'}:
                raise ValueError(f'Archivo privado no permitido: {rel}')
            files.add(rel.as_posix())
    return {rel: digest(root / rel, hash_mode=hash_mode) for rel in sorted(files)}


def validate_features(root, *, hash_mode=CURRENT_HASH_MODE):
    errors = []
    for rel, markers in FEATURES.items():
        path = root / rel
        content = path.read_text(encoding='utf-8') if path.is_file() else ''
        errors.extend(f'{rel}: falta {marker}' for marker in markers if marker not in content)
    assets = json.loads((ROOT / 'contracts/release_assets.json').read_text(encoding='utf-8'))
    for rel, expected in assets.items():
        path = root / rel
        if not path.is_file() or digest(path, hash_mode=hash_mode) != expected:
            errors.append(f'Identidad visual no aprobada: {rel}')
    if errors:
        raise ValueError('\n'.join(errors))


def manifest(root):
    validate_features(root, hash_mode=CURRENT_HASH_MODE)
    files = source_files(root, hash_mode=CURRENT_HASH_MODE)
    value = manifest_digest(files, hash_mode=CURRENT_HASH_MODE)
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    return {
        'base_revision': revision,
        'hash_mode': CURRENT_HASH_MODE,
        'content_sha256': value,
        'files': files,
    }


def verify(package):
    data = json.loads((package / 'release-manifest.json').read_text(encoding='utf-8'))
    files = data['files']
    hash_mode = data.get('hash_mode', HASH_MODE_RAW_V1)
    if hash_mode not in SUPPORTED_HASH_MODES:
        raise ValueError(f'Modo de huella no soportado: {hash_mode}')
    for rel, expected in files.items():
        path = package / rel
        if not path.resolve().is_relative_to(package.resolve()):
            raise ValueError('Ruta fuera del paquete')
        if not path.is_file() or digest(path, hash_mode=hash_mode) != expected:
            raise ValueError(f'Paquete modificado: {rel}')
    actual = {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
    permitted = set(files) | {'release-manifest.json', 'backend/release.json', 'frontend/static/release.json'}
    extra = actual - permitted
    if extra:
        raise ValueError(f'Archivos ajenos al manifiesto: {sorted(extra)}')
    expected_digest = manifest_digest(files, hash_mode=hash_mode)
    if expected_digest != data['content_sha256']:
        raise ValueError('Huella del manifiesto inválida')
    for rel in ('backend/release.json', 'frontend/static/release.json'):
        meta = json.loads((package / rel).read_text(encoding='utf-8'))
        if meta != {key: data[key] for key in ('base_revision', 'content_sha256')}:
            raise ValueError('Backend y frontend no pertenecen a la misma entrega')
    validate_features(package, hash_mode=hash_mode)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'package', 'verify'])
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--approved-sha256')
    args = parser.parse_args()
    if args.command == 'verify':
        if not args.destination:
            parser.error('verify requiere --destination')
        data = verify(args.destination.resolve())
    else:
        data = manifest(ROOT)
        if args.command == 'package':
            if args.approved_sha256 != data['content_sha256']:
                parser.error('Revisar check y proporcionar su --approved-sha256; el árbol cambió o no fue aprobado.')
            dest = args.destination
            if dest is None:
                parser.error('package requiere un directorio nuevo --destination')
            dest = dest.resolve()
            if not dest.is_relative_to(ROOT / 'tmp') or dest.exists():
                parser.error('El destino debe ser nuevo y estar dentro de tmp de la raíz canónica')
            dest.mkdir(parents=True)
            for rel in data['files']:
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, target)
            (dest / 'release-manifest.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
            metadata = json.dumps({key: data[key] for key in ('base_revision', 'content_sha256')})
            (dest / 'backend/release.json').write_text(metadata, encoding='utf-8')
            (dest / 'frontend/static/release.json').write_text(metadata, encoding='utf-8')
            verify(dest)
    print(json.dumps({key: value for key, value in data.items() if key != 'files'} | {'files': len(data['files'])}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        print(f'PUBLICACIÓN BLOQUEADA: {exc}', file=sys.stderr)
        sys.exit(1)
