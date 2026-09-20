import importlib.util
import json
from pathlib import Path
import sys

import pytest

from launch_migrations import LAUNCH_MIGRATION_SCRIPTS
from main import app

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_guard', ROOT / 'scripts/release_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
sys.modules.setdefault('release_guard', guard)
worker_spec = importlib.util.spec_from_file_location(
    'project_worker_release',
    ROOT / 'scripts/project_worker_release.py',
)
worker_release = importlib.util.module_from_spec(worker_spec)
worker_spec.loader.exec_module(worker_release)


def missing_contracts(operations):
    return set(json.loads((ROOT / 'contracts/operational_routes.json').read_text())) - operations


def test_every_approved_operational_contract_survives():
    operations = {method + ' ' + route.path for route in app.routes for method in getattr(route, 'methods', set())}
    assert not missing_contracts(operations)
    operations.remove('PUT /cotizaciones/{cotizacion_id}')
    assert 'PUT /cotizaciones/{cotizacion_id}' in missing_contracts(operations)


def test_critical_features_and_brand_assets_survive():
    guard.validate_features(ROOT)


def test_packager_excludes_secrets_auxiliary_versions_and_fixtures():
    files = guard.source_files(ROOT)
    assert files
    assert 'backend/main.py' in files
    assert 'backend/http_security.py' in files
    assert 'frontend/static/favicon.svg' in files
    assert not any('/.env' in name or '_release' in name or '/e2e/' in name or 'conftest' in name for name in files)
    assert 'backend/seed_demo_tenant.py' not in files
    assert 'backend/reset_db.py' not in files
    assert 'backend/reset_superadmin_password.py' not in files
    assert 'backend/set_fake_token.py' not in files
    assert 'backend/debug_emit.py' not in files
    assert 'backend/requirements-lock.txt' in files
    assert 'backend/requirements.in' in files
    assert 'backend/Dockerfile' in files
    assert 'backend/.dockerignore' in files


def test_packager_rejects_missing_local_backend_import(tmp_path):
    backend = tmp_path / 'backend'
    backend.mkdir()
    (backend / 'main.py').write_text('from http_security import apply\n', encoding='utf-8')
    (backend / 'http_security.py').write_text('def apply(): pass\n', encoding='utf-8')

    with pytest.raises(ValueError, match='http_security.py'):
        guard.validate_backend_import_closure(tmp_path, {'backend/main.py': 'digest'})

    guard.validate_backend_import_closure(
        tmp_path,
        {'backend/main.py': 'digest', 'backend/http_security.py': 'digest'},
    )


def test_packager_keeps_every_launch_migration_but_no_root_test_or_admin_tool():
    files = set(guard.source_files(ROOT))
    expected_migrations = {f'backend/{name}' for name in LAUNCH_MIGRATION_SCRIPTS}

    assert expected_migrations <= files
    assert not any(Path(name).name.startswith('test_') for name in files)
    assert 'backend/fix_superadmin.py' not in files
    assert 'backend/cleanup_beta_test_data.py' not in files


def test_dirty_runtime_files_block_release_but_support_files_do_not(monkeypatch):
    class Result:
        stdout = (
            b'backend/main.py\0'
            b'frontend/e2e/navigation.spec.js\0'
            b'backend/seed_demo_tenant.py\0'
            b'docs/RELEASE_CANONICO.md\0'
        )

    monkeypatch.setattr(guard.subprocess, 'run', lambda *args, **kwargs: Result())

    assert guard.dirty_release_paths(ROOT) == ['backend/main.py']
    with pytest.raises(ValueError, match='cambios sin commit'):
        guard.require_clean_release_tree(ROOT)


def test_missing_ui_feature_blocks_publication(tmp_path):
    with pytest.raises(ValueError, match='falta'):
        guard.validate_features(tmp_path)


def test_modified_package_is_rejected(tmp_path):
    (tmp_path / 'release-manifest.json').write_text(json.dumps({'files': {'module.py': 'bad'}}))
    (tmp_path / 'module.py').write_text('changed')
    with pytest.raises(ValueError, match='modificado'):
        guard.verify(tmp_path)


def test_canonical_text_digest_is_stable_across_line_endings(tmp_path):
    lf = tmp_path / 'lf.py'
    crlf = tmp_path / 'crlf.py'
    lf.write_bytes(b'first\nsecond\n')
    crlf.write_bytes(b'first\r\nsecond\r\n')

    assert guard.digest(lf) == guard.digest(crlf)
    assert guard.digest(lf, hash_mode=guard.HASH_MODE_RAW_V1) != guard.digest(
        crlf,
        hash_mode=guard.HASH_MODE_RAW_V1,
    )


def test_canonical_digest_preserves_binary_bytes_and_content_changes(tmp_path):
    original = tmp_path / 'original.bin'
    changed = tmp_path / 'changed.bin'
    original.write_bytes(b'prefix\x00\r\nsuffix')
    changed.write_bytes(b'prefix\x00\nsuffix')

    assert guard.digest(original) != guard.digest(changed)

    first_text = tmp_path / 'first.py'
    changed_text = tmp_path / 'changed.py'
    first_text.write_bytes(b'first\nsecond\n')
    changed_text.write_bytes(b'first\nchanged\n')
    assert guard.digest(first_text) != guard.digest(changed_text)


def test_manifest_digest_records_hash_mode():
    files = {'backend/main.py': 'abc'}

    canonical = guard.manifest_digest(
        files,
        hash_mode=guard.HASH_MODE_CANONICAL_TEXT_V1,
    )
    legacy = guard.manifest_digest(files, hash_mode=guard.HASH_MODE_RAW_V1)

    assert canonical != legacy


def test_verify_accepts_equivalent_crlf_package_in_canonical_mode(tmp_path, monkeypatch):
    source = tmp_path / 'source.py'
    source.write_bytes(b'first\nsecond\n')
    files = {'module.py': guard.digest(source)}
    data = {
        'base_revision': 'test-revision',
        'hash_mode': guard.HASH_MODE_CANONICAL_TEXT_V1,
        'content_sha256': guard.manifest_digest(
            files,
            hash_mode=guard.HASH_MODE_CANONICAL_TEXT_V1,
        ),
        'files': files,
    }
    package = tmp_path / 'package'
    (package / 'backend').mkdir(parents=True)
    (package / 'frontend/static').mkdir(parents=True)
    (package / 'module.py').write_bytes(b'first\r\nsecond\r\n')
    (package / 'release-manifest.json').write_text(json.dumps(data), encoding='utf-8')
    metadata = json.dumps(
        {key: data[key] for key in ('base_revision', 'content_sha256')}
    )
    (package / 'backend/release.json').write_text(metadata, encoding='utf-8')
    (package / 'frontend/static/release.json').write_text(metadata, encoding='utf-8')
    monkeypatch.setattr(guard, 'validate_features', lambda *args, **kwargs: None)

    assert guard.verify(package) == data


def test_legacy_manifest_uses_raw_hash_without_current_feature_markers(tmp_path):
    payload = tmp_path / 'module.py'
    payload.write_bytes(b'legacy\r\n')
    files = {
        'module.py': guard.digest(payload, hash_mode=guard.HASH_MODE_RAW_V1),
    }
    data = {
        'base_revision': 'legacy-revision',
        'content_sha256': guard.manifest_digest(
            files,
            hash_mode=guard.HASH_MODE_RAW_V1,
        ),
        'files': files,
    }
    (tmp_path / 'backend').mkdir()
    (tmp_path / 'frontend/static').mkdir(parents=True)
    (tmp_path / 'release-manifest.json').write_text(json.dumps(data), encoding='utf-8')
    metadata = json.dumps(
        {key: data[key] for key in ('base_revision', 'content_sha256')}
    )
    (tmp_path / 'backend/release.json').write_text(metadata, encoding='utf-8')
    (tmp_path / 'frontend/static/release.json').write_text(metadata, encoding='utf-8')

    assert guard.verify(tmp_path) == data


def test_unknown_hash_mode_is_rejected(tmp_path):
    (tmp_path / 'release-manifest.json').write_text(
        json.dumps({'hash_mode': 'unknown-v9', 'files': {}}),
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='no soportado'):
        guard.verify(tmp_path)


def test_release_gate_workflow_cannot_silently_drop_critical_checks():
    workflow = (ROOT / '.github/workflows/release-gate.yml').read_text(encoding='utf-8')
    for marker in (
        'test_release_guard.py',
        'test_operational_frontend_contracts.py',
        '--ignore=test_sale_dispatch_postgres.py',
        'npm test',
        'npm run lint',
        'npm run build',
        'backend/requirements-test.txt',
        'python -m pip check',
        'playwright install --with-deps chromium',
        'python scripts/run_e2e_local.py',
        'release_guard.py check',
        'Build worker container from canonical projection',
        'project_worker_release.py',
    ):
        assert marker in workflow


def test_production_images_install_the_pinned_runtime_lock():
    for path in (ROOT / 'Dockerfile', ROOT / 'backend/Dockerfile'):
        dockerfile = path.read_text(encoding='utf-8')
        assert 'requirements-lock.txt' in dockerfile
        assert 'pip install --no-cache-dir --upgrade -r /code/requirements-lock.txt' in dockerfile
    assert (ROOT / 'backend/requirements.txt').read_text(encoding='utf-8').strip() == '-r requirements-lock.txt'


def test_worker_projection_uses_verified_backend_docker_adapter(tmp_path, monkeypatch):
    source = tmp_path / 'package'
    (source / 'backend').mkdir(parents=True)
    backend_dockerfile = 'FROM python:3.11-slim\nCOPY ./requirements-lock.txt /code/requirements-lock.txt\n'
    railway_config = json.dumps({'build': {'builder': 'DOCKERFILE', 'dockerfilePath': 'Dockerfile'}})
    payloads = {
        'backend/Dockerfile': backend_dockerfile,
        'backend/.dockerignore': '*.log\n',
        'backend/main.py': 'app = object()\n',
        'railway.json': railway_config,
    }
    for relative, content in payloads.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    delivery = {
        'base_revision': 'worker-test',
        'hash_mode': guard.CURRENT_HASH_MODE,
        'content_sha256': 'canonical-worker-sha',
        'files': {
            relative: guard.digest(source / relative)
            for relative in payloads
        },
    }
    (source / 'release-manifest.json').write_text(
        json.dumps(delivery),
        encoding='utf-8',
    )
    (source / 'backend/release.json').write_text(
        json.dumps({
            'base_revision': delivery['base_revision'],
            'content_sha256': delivery['content_sha256'],
        }),
        encoding='utf-8',
    )

    monkeypatch.setattr(worker_release, 'ROOT', tmp_path)
    monkeypatch.setattr(worker_release, 'verify', lambda package: delivery)
    destination = tmp_path / 'tmp' / 'worker'

    projection = worker_release.project_worker_release(source, destination)

    assert (destination / 'Dockerfile').read_text(encoding='utf-8') == backend_dockerfile
    projected_railway = json.loads((destination / 'railway.json').read_text(encoding='utf-8'))
    assert projected_railway['build'] == json.loads(railway_config)['build']
    assert projected_railway['deploy']['startCommand'] == worker_release.WORKER_START_COMMAND
    assert 'run_emission_worker.py' in projected_railway['deploy']['startCommand']
    assert 'uvicorn' not in projected_railway['deploy']['startCommand']
    assert (destination / 'backend/main.py').read_text(encoding='utf-8') == payloads['backend/main.py']
    assert projection['builder'] == 'DOCKERFILE'
    assert projection['railway_root_directory'] == 'backend'
    assert projection['dockerfile_source'] == 'backend/Dockerfile'
    assert projection['adapter_hashes']['Dockerfile'] == delivery['files']['backend/Dockerfile']
    assert projection['adapter_source_hashes']['railway.json'] == delivery['files']['railway.json']
    assert projection['adapter_hashes']['railway.json'] == guard.digest(destination / 'railway.json')
    assert projection['start_command'] == worker_release.WORKER_START_COMMAND


def test_worker_projection_rejects_package_without_verified_dockerfile(tmp_path, monkeypatch):
    source = tmp_path / 'package'
    source.mkdir()
    delivery = {
        'hash_mode': guard.CURRENT_HASH_MODE,
        'content_sha256': 'missing-adapter',
        'files': {'railway.json': 'irrelevant'},
    }
    monkeypatch.setattr(worker_release, 'ROOT', tmp_path)
    monkeypatch.setattr(worker_release, 'verify', lambda package: delivery)

    with pytest.raises(ValueError, match='adaptadores worker verificados'):
        worker_release.project_worker_release(source, tmp_path / 'tmp' / 'worker')


def test_playwright_configuration_has_no_remote_execution_bypass():
    config = (ROOT / 'frontend/playwright.config.js').read_text(encoding='utf-8')
    assert 'E2E_ALLOW_REMOTE' not in config
    assert "assertSafeLocalUrl(baseURL" in config
    assert "assertSafeLocalUrl(apiURL" in config
