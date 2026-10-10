"""GitHub validation evidence safety tests using only synthetic API responses."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from urllib.request import Request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_ci_evidence as evidence

REPOSITORY = 'hkrojas/inkora_pse'
REVISION = 'a' * 40
HEAD = 'b' * 40
BASE = 'c' * 40
TREE = 'd' * 40
OTHER_TREE = 'e' * 40
FINGERPRINT = 'f' * 64


def run_data(event='pull_request'):
    return {'id': 123, 'status': 'completed', 'conclusion': 'success',
            'path': evidence.WORKFLOW, 'event': event,
            'head_repository': {'full_name': REPOSITORY},
            'head_sha': HEAD if event == 'pull_request' else REVISION,
            'head_branch': 'feature' if event == 'pull_request' else 'main',
            'pull_requests': [{'number': 48, 'head': {'sha': HEAD}, 'base': {'sha': BASE}}],
            'html_url': 'https://github.com/hkrojas/inkora_pse/actions/runs/123'}


def receipt_data(profile='frontend'):
    return {'schema': 1, 'policy_version': evidence.POLICY_VERSION,
            'repository': REPOSITORY, 'run_id': '123', 'workflow': evidence.WORKFLOW,
            'status': 'passed', 'profile': profile, 'tested_revision': REVISION,
            'tested_tree': TREE, 'backend_fingerprint': FINGERPRINT,
            'backend_validated': True, 'pull_request_number': 48,
            'specs': ['navigation.spec.js'], 'reused': False}


def pull_data():
    return {'number': 48, 'merged_at': '2026-10-10T00:00:00Z',
            'base': {'ref': 'main', 'repo': {'full_name': REPOSITORY}, 'sha': BASE},
            'head': {'repo': {'full_name': REPOSITORY}, 'sha': HEAD}}


def commit_data():
    return {'sha': REVISION, 'tree': {'sha': TREE},
            'parents': [{'sha': BASE}, {'sha': HEAD}]}


class FakeGitHub:
    repository = REPOSITORY

    def __init__(self, run=None, receipt=None, pull=None, commit=None):
        self.run = run or run_data()
        self.artifact = receipt if receipt is not None else receipt_data()
        self.pull = pull or pull_data()
        self.commit = commit or commit_data()
        self.calls = []

    def runs(self):
        return [self.run]

    def receipt(self, run):
        return self.artifact

    def request(self, path):
        self.calls.append(path)
        if path == 'pulls/48':
            return self.pull
        if path == f'git/commits/{REVISION}':
            return self.commit
        raise ValueError('Unexpected synthetic API path: ' + path)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.selection = {'profile': 'frontend', 'specs': ['navigation.spec.js'],
                          'tested_revision': REVISION, 'tested_tree': TREE,
                          'backend_fingerprint': FINGERPRINT}

    def select(self, github, *, reuse=False, fingerprint=FINGERPRINT):
        with patch.object(evidence, 'backend_fingerprint', return_value=fingerprint):
            return evidence.select_evidence(self.selection, github, allow_reuse=reuse)

    def assert_full(self, result):
        self.assertIs(result['reuse'], False)
        self.assertEqual(result['profile'], 'full')
        self.assertEqual(result['specs'], [])

    def test_identical_whole_tree_merged_pr_can_be_reused(self):
        result = self.select(FakeGitHub(), reuse=True)
        self.assertIs(result['reuse'], True)
        self.assertEqual(result['source_run_id'], 123)

    def test_different_current_tree_is_not_reused(self):
        self.selection['tested_tree'] = OTHER_TREE
        self.assert_full(self.select(FakeGitHub(), reuse=True))

    def test_different_commit_same_verified_tree_can_be_reused(self):
        self.selection['tested_revision'] = '1' * 40
        self.assertIs(self.select(FakeGitHub(), reuse=True)['reuse'], True)

    def test_claimed_tree_must_match_actual_commit_tree(self):
        commit = commit_data()
        commit['tree']['sha'] = OTHER_TREE
        self.assert_full(self.select(FakeGitHub(commit=commit), reuse=True))

    def test_pr_checkout_must_contain_the_run_head_as_merge_parent(self):
        commit = commit_data()
        commit['parents'][1]['sha'] = '2' * 40
        self.assert_full(self.select(FakeGitHub(commit=commit), reuse=True))

    def test_single_parent_pr_commit_is_not_accepted_as_tested_merge(self):
        commit = commit_data()
        commit['parents'] = [{'sha': HEAD}]
        self.assert_full(self.select(FakeGitHub(commit=commit), reuse=True))

    def test_unmerged_pr_and_wrong_target_are_not_reused(self):
        for field in ('unmerged', 'other_base', 'base_repo', 'fork_head'):
            with self.subTest(field=field):
                pull = pull_data()
                if field == 'unmerged':
                    pull['merged_at'] = None
                elif field == 'other_base':
                    pull['base']['ref'] = 'development'
                elif field == 'base_repo':
                    pull['base']['repo']['full_name'] = 'other/repo'
                else:
                    pull['head']['repo']['full_name'] = 'fork/repo'
                self.assert_full(self.select(FakeGitHub(pull=pull), reuse=True))

    def test_fork_failed_incomplete_or_other_workflow_run_is_not_reused(self):
        for key, value in (('status', 'in_progress'), ('conclusion', 'failure'),
                           ('conclusion', 'cancelled'), ('path', '.github/workflows/untrusted.yml'),
                           ('head_repository', {'full_name': 'fork/repo'})):
            with self.subTest(key=key, value=value):
                run = run_data()
                run[key] = value
                self.assert_full(self.select(FakeGitHub(run=run), reuse=True))

    def test_invalid_receipts_cannot_authorize_reuse(self):
        for key, value in (('schema', 2), ('policy_version', -1), ('repository', 'other/repo'),
                           ('run_id', 999), ('workflow', 'untrusted'), ('status', 'pending'),
                           ('profile', 'unknown'), ('tested_tree', 'not-a-tree')):
            with self.subTest(key=key):
                receipt = receipt_data()
                receipt[key] = value
                self.assert_full(self.select(FakeGitHub(receipt=receipt), reuse=True))

    def test_pr_number_must_belong_to_run(self):
        receipt = receipt_data()
        receipt['pull_request_number'] = 49
        self.assert_full(self.select(FakeGitHub(receipt=receipt), reuse=True))

    def test_merged_pr_with_cleared_run_association_is_bound_to_real_head(self):
        run = run_data()
        run['pull_requests'] = []
        self.assertIs(self.select(FakeGitHub(run=run), reuse=True)['reuse'], True)
        pull = pull_data()
        pull['head']['sha'] = '0' * 40
        self.assert_full(self.select(FakeGitHub(run=run, pull=pull), reuse=True))

    def test_missing_receipt_or_empty_history_falls_back_to_full(self):
        for kind in ('artifact', 'history'):
            with self.subTest(kind=kind):
                github = FakeGitHub()
                if kind == 'artifact':
                    github.receipt = lambda run: None
                else:
                    github.runs = lambda: []
                self.assert_full(self.select(github, reuse=True))

    def test_api_errors_during_runs_artifact_pull_or_commit_fail_closed(self):
        for step in ('runs', 'receipt', 'pull', 'commit'):
            with self.subTest(step=step):
                github = FakeGitHub()
                def fail(*args):
                    raise OSError('synthetic API unavailable')
                if step in ('runs', 'receipt'):
                    setattr(github, step, fail)
                else:
                    original = github.request
                    prefix = 'pulls/' if step == 'pull' else 'git/commits/'
                    def request(path):
                        return fail() if path.startswith(prefix) else original(path)
                    github.request = request
                self.assert_full(self.select(github, reuse=True))

    def test_full_main_baseline_can_allow_frontend_validation(self):
        github = FakeGitHub(run=run_data('push'), receipt=receipt_data('full'))
        result = self.select(github)
        self.assertFalse(result['reuse'])
        self.assertEqual(result['profile'], 'frontend')
        self.assertEqual(result['backend_baseline']['run_id'], 123)

    def test_full_baseline_mismatch_or_unvalidated_is_rejected(self):
        for key, value in (('backend_fingerprint', '0' * 64), ('backend_validated', False),
                           ('profile', 'frontend')):
            with self.subTest(key=key):
                receipt = receipt_data('full')
                receipt[key] = value
                self.assert_full(self.select(FakeGitHub(run=run_data('push'), receipt=receipt)))

    def test_main_full_receipt_inherited_from_verified_pr_remains_a_baseline(self):
        receipt = receipt_data('full')
        receipt.update(reused=True, source_run_id=122,
                       source_run_url='https://github.com/hkrojas/inkora_pse/actions/runs/122')
        result = self.select(FakeGitHub(run=run_data('push'), receipt=receipt))
        self.assertEqual(result['profile'], 'frontend')
        self.assertFalse(result['reuse'])
        self.assertTrue(result['backend_validated'])

    def test_actual_baseline_fingerprint_must_match_not_just_claim(self):
        github = FakeGitHub(run=run_data('push'), receipt=receipt_data('full'))
        self.assert_full(self.select(github, fingerprint='0' * 64))

    def test_baseline_from_branch_or_pr_is_not_trusted(self):
        for event, branch in (('push', 'feature'), ('workflow_dispatch', 'feature'),
                              ('pull_request', 'main')):
            with self.subTest(event=event, branch=branch):
                run = run_data(event)
                run['head_branch'] = branch
                self.assert_full(self.select(FakeGitHub(run=run, receipt=receipt_data('full'))))

    def test_push_baseline_must_use_exact_run_head_revision(self):
        run = run_data('push')
        run['head_sha'] = '9' * 40
        self.assert_full(self.select(FakeGitHub(run=run, receipt=receipt_data('full'))))

    def test_unavailable_local_git_object_never_authorizes_backend_baseline(self):
        github = FakeGitHub(run=run_data('push'), receipt=receipt_data('full'))
        with patch.object(evidence, 'backend_fingerprint', side_effect=subprocess.CalledProcessError(128, 'git')):
            self.assert_full(evidence.select_evidence(self.selection, github))

    def test_api_error_after_partial_baseline_discards_shortcut(self):
        github = FakeGitHub(run=run_data('push'), receipt=receipt_data('full'))
        later = run_data()
        later['id'] = 124
        github.runs = lambda: [github.run, later]
        original = github.receipt
        def receipt(run):
            if run['id'] == 124:
                raise OSError('later evidence unavailable')
            return original(run)
        github.receipt = receipt
        self.assert_full(self.select(github, reuse=True))

    def test_artifact_redirect_drops_api_authorization(self):
        request = Request('https://api.github.com/repos/a/b/actions/artifacts/1/zip',
                          headers={'Authorization': 'Bearer synthetic-secret'})
        redirected = evidence.SafeRedirect().redirect_request(
            request, None, 302, 'Found', {}, 'https://storage.example.test/signed-artifact')
        self.assertIsNone(redirected.get_header('Authorization'))


class ReceiptArchiveTests(unittest.TestCase):
    def archive(self, files):
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as bundle:
            for name, content in files.items():
                bundle.writestr(name, content)
        return output.getvalue()

    def client(self, archive, *, expired=False, duplicates=False):
        client = object.__new__(evidence.GitHub)
        artifact = {'id': 12, 'name': evidence.ARTIFACT, 'expired': expired}
        artifacts = [artifact, copy.deepcopy(artifact)] if duplicates else [artifact]
        client.request = lambda path, binary=False: archive if binary else {'artifacts': artifacts}
        return client

    def test_single_small_expected_json_receipt_is_read(self):
        archive = self.archive({evidence.RECEIPT_FILE: json.dumps(receipt_data())})
        self.assertEqual(self.client(archive).receipt(run_data())['run_id'], '123')

    def test_expired_duplicate_extra_path_or_oversized_receipt_is_rejected(self):
        good = self.archive({evidence.RECEIPT_FILE: '{}'})
        self.assertIsNone(self.client(good, expired=True).receipt(run_data()))
        self.assertIsNone(self.client(good, duplicates=True).receipt(run_data()))
        for files in ({'../' + evidence.RECEIPT_FILE: '{}'},
                      {evidence.RECEIPT_FILE: '{}', 'other.txt': 'extra'},
                      {evidence.RECEIPT_FILE: ' ' * 100_001}):
            with self.subTest(names=list(files)):
                self.assertIsNone(self.client(self.archive(files)).receipt(run_data()))


if __name__ == '__main__':
    unittest.main()
