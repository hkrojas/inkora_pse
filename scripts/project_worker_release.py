"""Build a verified worker bundle for Railway's existing backend-root service.

Railway applies the worker service's ``rootDirectory=backend`` to the build
context, while it reads ``railway.json`` and its Dockerfile path from the
uploaded bundle root.  The adapter files generated here deliberately point to
the backend-scoped Dockerfile; the worker's remote start command and
environment remain unchanged.
"""
import argparse
import json
from pathlib import Path
import shutil

from release_guard import ROOT, digest, verify


def project_worker_release(source: Path, destination: Path) -> dict:
    source, destination = source.resolve(), destination.resolve()
    delivery = verify(source)
    hash_mode = delivery.get('hash_mode', 'raw-v1')
    if destination.exists() or not destination.is_relative_to(ROOT / 'tmp'):
        raise ValueError('El destino debe ser NUEVO dentro de tmp')

    required_adapter_sources = ('backend/Dockerfile', 'railway.json')
    missing = [path for path in required_adapter_sources if path not in delivery['files']]
    if missing:
        raise ValueError(f'El paquete no contiene adaptadores worker verificados: {missing}')

    destination.mkdir(parents=True)
    backend = {
        path: checksum
        for path, checksum in delivery['files'].items()
        if path.startswith('backend/')
    }
    for relative, checksum in backend.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
        if digest(target, hash_mode=hash_mode) != checksum:
            raise ValueError(f'Proyeccion divergente: {relative}')

    # release.json is generated package metadata and therefore intentionally
    # lives outside delivery["files"], but it must travel with the worker.
    shutil.copy2(source / 'backend/release.json', destination / 'backend/release.json')

    adapters = {
        'Dockerfile': 'backend/Dockerfile',
        'railway.json': 'railway.json',
    }
    adapter_hashes = {}
    for target_name, source_name in adapters.items():
        target = destination / target_name
        shutil.copy2(source / source_name, target)
        expected = delivery['files'][source_name]
        actual = digest(target, hash_mode=hash_mode)
        if actual != expected:
            raise ValueError(f'Adaptador worker divergente: {target_name}')
        adapter_hashes[target_name] = actual

    projection = {
        'content_sha256': delivery['content_sha256'],
        'files': backend,
        'source_manifest_sha256': digest(
            source / 'release-manifest.json',
            hash_mode=hash_mode,
        ),
        'railway_root_directory': 'backend',
        'builder': 'DOCKERFILE',
        'dockerfile_source': 'backend/Dockerfile',
        'adapter_hashes': adapter_hashes,
    }
    (destination / 'worker-projection.json').write_text(
        json.dumps(projection, indent=2),
        encoding='utf-8',
    )
    return projection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    try:
        projection = project_worker_release(args.source, args.destination)
    except ValueError as exc:
        parser.error(str(exc))
    print(
        f'Worker: {len(projection["files"])} archivos identicos; '
        f'entrega {projection["content_sha256"]}'
    )


if __name__ == '__main__':
    main()
