"""Project the SAME frozen backend into Railway's existing backend-root service.

No root Dockerfile/railway.json: those describe the API's root build context.
The worker's existing Railway start command, environment and root are retained.
"""
import argparse
import json
from pathlib import Path
import shutil

from release_guard import ROOT, digest, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    delivery = verify(source)
    if destination.exists() or not destination.is_relative_to(ROOT / 'tmp'):
        parser.error('El destino debe ser NUEVO dentro de tmp')
    destination.mkdir(parents=True)
    backend = {path: checksum for path, checksum in delivery['files'].items() if path.startswith('backend/')}
    for relative, checksum in backend.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
        if digest(target) != checksum:
            raise ValueError(f'Proyección divergente: {relative}')
    shutil.copy2(source / 'backend/release.json', destination / 'backend/release.json')
    (destination / 'worker-projection.json').write_text(json.dumps({
        'content_sha256': delivery['content_sha256'], 'files': backend,
        'source_manifest_sha256': digest(source / 'release-manifest.json'),
        'railway_root_directory': 'backend', 'builder': 'RAILPACK',
    }, indent=2), encoding='utf-8')
    print(f'Worker: {len(backend)} archivos idénticos; entrega {delivery["content_sha256"]}')


if __name__ == '__main__':
    main()
