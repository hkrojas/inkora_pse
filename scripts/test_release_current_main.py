"""Isolated stdlib tests for the opt-in production main freshness gate.

Run with: python -m unittest discover -s scripts -p test_release_current_main.py
All Git fetches use temporary local remotes; no network or app services.
"""
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).with_name('release_guard.py')
SPEC = importlib.util.spec_from_file_location('release_guard_current_main_test', SCRIPT)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class CurrentMainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='inkora_release_current_main_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote.git'
        self.repo = self.root / 'candidate'
        self.publisher = self.root / 'publisher'
        self.git(self.root, 'init', '--bare', str(self.remote))
        self.git(self.root, 'init', '-b', 'main', str(self.repo))
        self.configure(self.repo)
        self.write('backend/main.py', 'app = None\n')
        self.write('frontend/static/icon.svg', '<svg/>\n')
        self.write('contracts/release_assets.json', '{}\n')
        self.write('scripts/support.py', '# delivery tool\n')
        self.commit(self.repo, 'initial main')
        self.initial = self.git(self.repo, 'rev-parse', 'HEAD')
        self.git(self.repo, 'remote', 'add', 'inkora_pse', str(self.remote))
        self.git(self.repo, 'push', 'inkora_pse', 'HEAD:refs/heads/main')
        self.git(self.root, 'clone', '--branch', 'main', str(self.remote), str(self.publisher))
        self.configure(self.publisher)

    def git(self, root, *args):
        result = subprocess.run(
            ['git', '-C', str(root), *args], capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()

    def configure(self, root):
        self.git(root, 'config', 'user.name', 'Isolated release test')
        self.git(root, 'config', 'user.email', 'release@example.test')
        self.git(root, 'config', 'core.autocrlf', 'false')
        self.git(root, 'config', 'commit.gpgsign', 'false')

    def write(self, path, content, *, root=None):
        target = (root or self.repo) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def commit(self, root, message):
        self.git(root, 'add', '.')
        self.git(root, 'commit', '-m', message)

    def advance_remote(self):
        self.write('scripts/support.py', '# newer delivery tool\n', root=self.publisher)
        self.commit(self.publisher, 'remote advances')
        self.git(self.publisher, 'push', 'origin', 'HEAD:refs/heads/main')
        return self.git(self.publisher, 'rev-parse', 'HEAD')

    def run_main(self, *args):
        stdout = io.StringIO()
        # Fixtures need no real application feature markers or pinned assets.
        with patch.object(guard, 'ROOT', self.repo), patch.object(guard, 'FEATURES', {}), \
                patch('sys.argv', [str(SCRIPT), *args]), redirect_stdout(stdout):
            guard.main()
        return json.loads(stdout.getvalue())

    def test_current_main_passes(self):
        guard.require_current_main(self.repo)

    def test_old_head_is_rejected_even_with_identical_tree(self):
        self.git(self.repo, 'commit', '--allow-empty', '-m', 'same tree new main')
        self.git(self.repo, 'push', 'inkora_pse', 'HEAD:refs/heads/main')
        self.git(self.repo, 'checkout', '--detach', self.initial)
        with self.assertRaisesRegex(ValueError, 'no coincide'):
            guard.require_current_main(self.repo)

    def test_remote_advance_is_fetched_instead_of_using_stale_tracking_ref(self):
        self.advance_remote()
        self.assertEqual(self.initial, self.git(self.repo, 'rev-parse', 'refs/remotes/inkora_pse/main'))
        with self.assertRaisesRegex(ValueError, 'no coincide'):
            guard.require_current_main(self.repo)

    def test_merge_equal_to_published_main_passes(self):
        newer = self.advance_remote()
        self.git(self.repo, 'fetch', 'inkora_pse', 'main')
        self.git(self.repo, 'merge', '--ff-only', newer)
        guard.require_current_main(self.repo)

    def test_actual_merge_commit_equal_to_published_main_passes(self):
        self.git(self.repo, 'switch', '-c', 'candidate-feature')
        self.write('feature.txt', 'feature\n')
        self.commit(self.repo, 'feature')
        self.git(self.repo, 'switch', 'main')
        self.git(self.repo, 'merge', '--no-ff', 'candidate-feature', '-m', 'merge feature')
        self.git(self.repo, 'push', 'inkora_pse', 'HEAD:refs/heads/main')
        guard.require_current_main(self.repo)

    def test_unstaged_non_runtime_tracked_tool_is_rejected(self):
        self.write('scripts/support.py', '# changed\n')
        with self.assertRaisesRegex(ValueError, 'archivos seguidos'):
            guard.require_current_main(self.repo)

    def test_staged_change_is_rejected_even_when_worktree_matches_head(self):
        self.write('scripts/support.py', '# staged change\n')
        self.git(self.repo, 'add', 'scripts/support.py')
        self.write('scripts/support.py', '# delivery tool\n')
        with self.assertRaisesRegex(ValueError, 'archivos seguidos'):
            guard.require_current_main(self.repo)

    def test_missing_remote_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'no está configurado'):
            guard.require_current_main(self.repo, remote='missing')

    def test_failed_fetch_does_not_fall_back_to_cached_main(self):
        self.git(self.repo, 'remote', 'set-url', 'inkora_pse', str(self.root / 'missing.git'))
        with self.assertRaisesRegex(ValueError, 'No se pudo comprobar'):
            guard.require_current_main(self.repo)

    def test_explicit_remote_is_supported(self):
        self.git(self.repo, 'remote', 'rename', 'inkora_pse', 'production')
        result = self.run_main('check', '--require-current-main', '--remote', 'production')
        self.assertEqual(result['base_revision'], self.initial)

    def test_default_check_remains_offline_and_compatible(self):
        self.git(self.repo, 'remote', 'remove', 'inkora_pse')
        result = self.run_main('check')
        self.assertEqual(result['base_revision'], self.initial)

    def test_package_checks_main_before_creating_destination(self):
        identity = self.run_main('check')
        self.advance_remote()
        dest = self.repo / 'tmp' / 'release'
        with self.assertRaisesRegex(ValueError, 'no coincide'):
            self.run_main('package', '--require-current-main', '--approved-sha256',
                          identity['content_sha256'], '--destination', str(dest))
        self.assertFalse(dest.exists())

    def test_package_on_current_main_preserves_manifest_and_metadata(self):
        identity = self.run_main('check', '--require-current-main')
        dest = self.repo / 'tmp' / 'release'
        result = self.run_main('package', '--require-current-main', '--approved-sha256',
                               identity['content_sha256'], '--destination', str(dest))
        self.assertEqual(result, identity)
        self.assertEqual(self.run_main('verify', '--destination', str(dest)), identity)

    def test_untracked_runtime_file_still_blocks_manifest(self):
        self.write('frontend/static/extra.svg', '<svg/>\n')
        with self.assertRaisesRegex(ValueError, 'contenido publicable tiene cambios'):
            self.run_main('check', '--require-current-main')

    def test_historical_raw_manifest_remains_verifiable_offline(self):
        package = self.root / 'historical-release'
        package.mkdir()
        self.write('backend/main.py', 'historical = True\r\n', root=package)
        files = {'backend/main.py': guard.digest(package / 'backend/main.py', hash_mode=guard.HASH_MODE_RAW_V1)}
        data = {'base_revision': 'historical-before-main',
                'content_sha256': guard.manifest_digest(files, hash_mode=guard.HASH_MODE_RAW_V1),
                'files': files}
        (package / 'release-manifest.json').write_text(json.dumps(data), encoding='utf-8')
        meta = {key: data[key] for key in ('base_revision', 'content_sha256')}
        for path in ('backend/release.json', 'frontend/static/release.json'):
            self.write(path, json.dumps(meta), root=package)
        self.git(self.repo, 'remote', 'remove', 'inkora_pse')
        result = self.run_main('verify', '--destination', str(package))
        self.assertEqual(result['base_revision'], 'historical-before-main')

    def test_verify_rejects_current_main_flag(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as failure:
            self.run_main('verify', '--require-current-main', '--destination', str(self.root))
        self.assertEqual(failure.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
