"""Conservative scope selection tests; no application services or network."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_scope as scope


class ClassificationTests(unittest.TestCase):
    def select(self, *entries, before='', after=''):
        return scope.classify(entries, lambda path: (before, after))

    def test_empty_diff_cannot_skip_runtime_validation_as_documentation(self):
        self.assertEqual(self.select()['profile'], 'full')

    def test_mixed_backend_and_global_css_is_full_in_either_order(self):
        backend = ('M', 'backend/routers/documentos.py')
        css = ('M', 'frontend/src/styles/globals.css')
        for entries in ((backend, css), (css, backend)):
            with self.subTest(entries=entries):
                self.assertEqual(self.select(*entries)['profile'], 'full')

    def test_unknown_after_shared_frontend_still_requires_full(self):
        self.assertEqual(self.select(('M', 'frontend/src/components/Sidebar.jsx'),
                                     ('M', 'unexpected.txt'))['profile'], 'full')

    def test_unknown_and_sensitive_files_are_full(self):
        for path in ('unexpected.txt', 'frontend/src/lib/utils/money.js', 'frontend/src/App.jsx',
                     'frontend/package-lock.json', 'contracts/operational_routes.json',
                     'scripts/release_scope.py', '.github/workflows/release-gate.yml'):
            with self.subTest(path=path):
                self.assertEqual(self.select(('M', path))['profile'], 'full')

    def test_add_delete_and_rename_always_require_full_even_for_known_paths(self):
        for status in ('A', 'D', 'R100', 'C100', 'T', 'U'):
            with self.subTest(status=status):
                self.assertEqual(self.select((status, 'frontend/src/pages/FacturasPage.jsx'))['profile'], 'full')

    def test_scoped_document_css_is_visual_and_keeps_smoke_and_documents(self):
        result = self.select(('M', 'frontend/src/styles/globals.css'),
                             before='.document-list-table td { padding: 12px; }',
                             after='.document-list-table td { padding: 10px; }')
        self.assertEqual(result['profile'], 'visual')
        self.assertEqual(set(result['specs']), scope.SMOKE | scope.DOCUMENTS)

    def test_scoped_media_container_css_is_visual(self):
        result = self.select(('M', 'frontend/src/styles/globals.css'),
                             before='@media (max-width: 900px) { .document-list-table td { padding: 12px; } }',
                             after='@media (max-width: 900px) { .document-list-table td { padding: 10px; } }')
        self.assertEqual(result['profile'], 'visual')

    def test_exact_document_table_root_is_visual(self):
        result = self.select(('M', 'frontend/src/styles/globals.css'),
                             before='.document-list-table { padding: 12px; }',
                             after='.document-list-table { padding: 10px; }')
        self.assertEqual(result['profile'], 'visual')

    def test_root_and_outside_selectors_require_all_frontend_flows(self):
        for selector in (':root', 'body', '.other-table', '.document-list-table, body',
                         '.document-list-table + .sidebar', '.document-list-table ~ .sidebar',
                         '.document-list-table:has(.warning)', '.document-list-table:global(.x)'):
            with self.subTest(selector=selector):
                result = self.select(('M', 'frontend/src/styles/globals.css'),
                                     before=f'{selector} {{ color: red; }}',
                                     after=f'{selector} {{ color: blue; }}')
                self.assertEqual(result['profile'], 'frontend')
                self.assertEqual(result['specs'], [])

    def test_mixed_scoped_and_global_css_is_not_visual(self):
        before = '.document-list-table td { color: red; } body { color: red; }'
        after = '.document-list-table td { color: blue; } body { color: blue; }'
        result = self.select(('M', 'frontend/src/styles/globals.css'), before=before, after=after)
        self.assertEqual(result['profile'], 'frontend')
        self.assertEqual(result['specs'], [])

    def test_unsupported_or_unbalanced_css_is_not_visual(self):
        for text in ('.document-list-table td { color: blue;',
                     '.document-list-table td { & span { color: blue; } }',
                     '@keyframes example { from { opacity: 0; } to { opacity: 1; } }',
                     '@import "other.css";'):
            with self.subTest(text=text):
                result = self.select(('M', 'frontend/src/styles/globals.css'), before='', after=text)
                self.assertEqual(result['profile'], 'frontend')

    def test_document_component_is_frontend_with_affected_specs(self):
        result = self.select(('M', 'frontend/src/components/documents/DocumentList.jsx'))
        self.assertEqual(result['profile'], 'frontend')
        self.assertTrue(scope.DOCUMENTS <= set(result['specs']))

    def test_scoped_css_does_not_reduce_shared_component_coverage(self):
        result = self.select(('M', 'frontend/src/styles/globals.css'),
                             ('M', 'frontend/src/components/ui/Pagination.jsx'),
                             before='.document-list-table td { padding: 12px; }',
                             after='.document-list-table td { padding: 10px; }')
        self.assertEqual(result['profile'], 'frontend')
        self.assertEqual(result['specs'], [])

    def test_shared_select_calendar_and_pagination_cover_all_browser_flows(self):
        for component in ('CustomSelect', 'DatePicker', 'Pagination'):
            with self.subTest(component=component):
                result = self.select(('M', f'frontend/src/components/ui/{component}.jsx'))
                self.assertEqual(result['profile'], 'frontend')
                self.assertEqual(result['specs'], [])

    def test_docs_only_has_no_browser_specs(self):
        result = self.select(('M', 'docs/RELEASE_CANONICO.md'))
        self.assertEqual(result['profile'], 'docs')
        self.assertEqual(result['specs'], [])


class GitScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='inkora_scope_')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Scope test')
        self.git('config', 'user.email', 'scope@example.test')
        self.git('config', 'core.autocrlf', 'false')
        self.git('config', 'commit.gpgsign', 'false')
        self.write('backend/test_domain.py', '# baseline\n')
        self.write('scripts/release_scope.py', '# policy baseline\n')
        self.write('frontend/src/pages/FacturasPage.jsx', '// baseline\n')
        self.write('docs/example.md', 'baseline\n')
        self.commit('baseline')
        self.base = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True,
                                       stderr=subprocess.DEVNULL).strip()

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-m', message)

    def test_rename_is_classified_as_delete_and_add_and_full(self):
        self.git('mv', 'frontend/src/pages/FacturasPage.jsx', 'frontend/src/pages/BoletasPage.jsx')
        self.commit('rename')
        selection = scope.plan(self.base, root=self.repo)
        self.assertEqual(selection['profile'], 'full')
        self.assertEqual({row['status'] for row in selection['changes']}, {'A', 'D'})

    def test_known_file_deletion_requires_full(self):
        self.git('rm', 'frontend/src/pages/FacturasPage.jsx')
        self.commit('delete')
        self.assertEqual(scope.plan(self.base, root=self.repo)['profile'], 'full')

    def test_nonancestor_base_is_rejected(self):
        self.git('switch', '-c', 'divergent')
        self.write('docs/example.md', 'divergent\n')
        self.commit('divergent')
        divergent = self.git('rev-parse', 'HEAD')
        self.git('switch', 'main')
        self.write('docs/example.md', 'main advances\n')
        self.commit('main advances')
        with self.assertRaises(subprocess.CalledProcessError):
            scope.plan(divergent, root=self.repo)

    def test_backend_fingerprint_covers_tests_and_gate_policy(self):
        initial = scope.backend_fingerprint(self.base, self.repo)
        for path in ('backend/test_domain.py', 'scripts/release_scope.py'):
            with self.subTest(path=path):
                self.write(path, '# changed\n')
                self.commit('change ' + path)
                updated = scope.backend_fingerprint(root=self.repo)
                self.assertNotEqual(initial, updated)
                initial = updated

    def test_frontend_and_docs_changes_do_not_invalidate_backend_fingerprint(self):
        initial = scope.backend_fingerprint(root=self.repo)
        self.write('frontend/src/pages/FacturasPage.jsx', '// new layout\n')
        self.write('docs/example.md', 'updated\n')
        self.commit('presentation/docs')
        self.assertEqual(initial, scope.backend_fingerprint(root=self.repo))

    def test_root_tooling_configuration_invalidates_backend_fingerprint(self):
        initial = scope.backend_fingerprint(root=self.repo)
        for path in ('pytest.ini', '.npmrc'):
            with self.subTest(path=path):
                self.write(path, '# tooling configuration\n')
                self.commit('add ' + path)
                updated = scope.backend_fingerprint(root=self.repo)
                self.assertNotEqual(initial, updated)
                initial = updated


if __name__ == '__main__':
    unittest.main()
