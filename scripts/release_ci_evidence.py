"""Read GitHub evidence; missing/expired evidence always runs tests again.

No deployment, mutation or credential output. Receipts are accepted only from
successful runs of this repository's release workflow, never from a local file.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import Request, build_opener, HTTPRedirectHandler
import zipfile

from release_scope import POLICY_VERSION, backend_fingerprint, git, plan, tree

WORKFLOW = '.github/workflows/release-gate.yml'
ARTIFACT = 'release-validation-receipt'
RECEIPT_FILE = 'validation-receipt.json'


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            # Artifact storage gets a signed URL, never the GitHub API token.
            redirected.remove_header('Authorization')
        return redirected


class GitHub:
    def __init__(self, repository):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Invalid repository')
        self.repository = repository
        self.token = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
        if not self.token and not os.getenv('CI'):
            try:
                self.token = subprocess.check_output(['gh', 'auth', 'token'], text=True,
                                                     stderr=subprocess.DEVNULL).strip()
            except (OSError, subprocess.CalledProcessError):
                pass
        self.opener = build_opener(SafeRedirect())

    def request(self, path, binary=False):
        headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        request = Request(f'https://api.github.com/repos/{self.repository}/{path}', headers=headers)
        with self.opener.open(request, timeout=15) as response:
            data = response.read(1_000_001)
        if len(data) > 1_000_000:
            raise ValueError('Evidence too large')
        return data if binary else json.loads(data)

    def runs(self):
        data = self.request('actions/workflows/release-gate.yml/runs?status=success&per_page=30')
        return data['workflow_runs']

    def receipt(self, run):
        artifacts = self.request(f'actions/runs/{run["id"]}/artifacts')['artifacts']
        matches = [item for item in artifacts if item['name'] == ARTIFACT and not item['expired']]
        if len(matches) != 1:
            return None
        archive = self.request(f'actions/artifacts/{matches[0]["id"]}/zip', binary=True)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            if bundle.namelist() != [RECEIPT_FILE] or bundle.getinfo(RECEIPT_FILE).file_size > 100_000:
                return None
            return json.loads(bundle.read(RECEIPT_FILE))


def trusted_run(run, repository):
    return (run.get('status') == 'completed' and run.get('conclusion') == 'success'
            and run.get('path') == WORKFLOW
            and run.get('head_repository', {}).get('full_name') == repository
            and run.get('event') in {'pull_request', 'push', 'workflow_dispatch'})


def trusted_receipt(receipt, run, repository):
    return (isinstance(receipt, dict) and receipt.get('schema') == 1
            and receipt.get('policy_version') == POLICY_VERSION
            and receipt.get('repository') == repository
            and str(receipt.get('run_id')) == str(run['id'])
            and receipt.get('workflow') == WORKFLOW
            and receipt.get('status') == 'passed'
            and receipt.get('profile') in {'full', 'frontend', 'visual', 'docs'}
            and bool(re.fullmatch(r'[a-f0-9]{40}', receipt.get('tested_tree', ''))))


def verified_checkout(receipt, run, get_commit):
    revision = receipt.get('tested_revision', '')
    if not re.fullmatch(r'[a-f0-9]{40}', revision):
        return False
    commit = get_commit(revision)
    if commit.get('sha') != revision or commit.get('tree', {}).get('sha') != receipt['tested_tree']:
        return False
    if run['event'] == 'pull_request':
        parents = commit.get('parents', [])
        return len(parents) == 2 and parents[1].get('sha') == run['head_sha']
    return revision == run.get('head_sha') and run.get('head_branch') == 'main'


def reusable_pr(receipt, run, current_tree, repository, get_pull, get_commit):
    if not trusted_run(run, repository) or not trusted_receipt(receipt, run, repository):
        return False
    if run['event'] != 'pull_request' or receipt['tested_tree'] != current_tree:
        return False
    if not verified_checkout(receipt, run, get_commit):
        return False
    number = receipt.get('pull_request_number')
    associations = run.get('pull_requests', [])
    if not number or (associations and number not in [item.get('number') for item in associations]):
        return False
    # GitHub can clear run.pull_requests after merge. Bind the recorded number
    # to the real merged PR head and the verified merge commit instead.
    pull = get_pull(number)
    return bool(pull.get('merged_at') and pull.get('base', {}).get('ref') == 'main'
                and pull.get('number') == number and pull.get('head', {}).get('sha') == run['head_sha']
                and pull.get('base', {}).get('repo', {}).get('full_name') == repository
                and pull.get('head', {}).get('repo', {}).get('full_name') == repository)


def full_backend_proof(receipt, run, fingerprint, repository, get_commit,
                       fingerprint_of=None):
    fingerprint_of = fingerprint_of or backend_fingerprint
    return (trusted_run(run, repository) and trusted_receipt(receipt, run, repository)
            and run['event'] in {'push', 'workflow_dispatch'} and run.get('head_branch') == 'main'
            and receipt['profile'] == 'full'
            and receipt.get('backend_fingerprint') == fingerprint
            and receipt.get('backend_validated') is True
            and verified_checkout(receipt, run, get_commit)
            and fingerprint_of(run['head_sha']) == fingerprint)


def select_evidence(selection, github, allow_reuse=False):
    baseline = None
    try:
        for run in github.runs():
            if not trusted_run(run, github.repository):
                continue
            receipt = github.receipt(run)
            if receipt is None:
                continue
            get_commit = lambda revision: github.request(f'git/commits/{revision}')
            if allow_reuse and reusable_pr(receipt, run, selection['tested_tree'], github.repository,
                                            lambda number: github.request(f'pulls/{number}'), get_commit):
                return {'reuse': True, 'profile': receipt['profile'], 'specs': receipt.get('specs', []),
                        'source_run_id': run['id'], 'source_run_url': run['html_url'],
                        'backend_validated': receipt.get('backend_validated', False)}
            if full_backend_proof(receipt, run, selection['backend_fingerprint'], github.repository, get_commit):
                baseline = {'run_id': run['id'], 'url': run['html_url']}
                if not allow_reuse:
                    break
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError, zipfile.BadZipFile):
        # API errors never authorize a shortcut, even after a partial search.
        return {'reuse': False, 'profile': 'full', 'specs': [],
                'evidence_reason': 'Missing or unreadable GitHub evidence'}
    if selection['profile'] in {'visual', 'frontend'} and baseline is None:
        return {'reuse': False, 'profile': 'full', 'specs': [],
                'evidence_reason': 'No successful full gate for identical backend/dependencies/policy'}
    return {'reuse': False, 'profile': selection['profile'], 'specs': selection['specs'],
            'backend_baseline': baseline, 'backend_validated': baseline is not None}


def create_receipt(selection, repository):
    if git('diff', '--name-only') or git('diff', '--cached', '--name-only'):
        raise ValueError('Tracked files changed during validation')
    if tree() != selection['tested_tree']:
        raise ValueError('Validated Git tree changed')
    return {**selection, 'schema': 1, 'repository': repository, 'workflow': WORKFLOW,
            'run_id': os.getenv('GITHUB_RUN_ID', 'local'),
            'pull_request_number': int(os.getenv('RELEASE_PR_NUMBER') or 0),
            'status': 'passed', 'reused': selection.get('reuse', False),
            'backend_validated': selection['profile'] == 'full' or selection.get('backend_validated', False),
            'completed_at': datetime.now(timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'receipt', 'e2e'])
    parser.add_argument('--base')
    parser.add_argument('--repository', default='hkrojas/inkora_pse')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--full', action='store_true', help='Only raises validation; cannot lower it')
    parser.add_argument('--reuse-merged-pr', action='store_true')
    args = parser.parse_args()
    if args.command == 'e2e':
        selection = json.loads(args.plan.read_text(encoding='utf-8-sig'))
        if tree() != selection['tested_tree']:
            raise ValueError('Plan no longer matches HEAD')
        command = [sys.executable, str(Path(__file__).with_name('run_e2e_local.py')), '--timeout-ms', '60000']
        for spec in selection['specs']:
            command.extend(['--spec', f'frontend/e2e/{spec}'])
        raise SystemExit(subprocess.run(command).returncode)
    if not args.output:
        parser.error('--output is required')
    if args.command == 'receipt':
        value = create_receipt(json.loads(args.plan.read_text(encoding='utf-8-sig')), args.repository)
    else:
        try:
            value = plan(args.base or 'HEAD^')
        except (OSError, ValueError, subprocess.CalledProcessError):
            value = {'policy_version': POLICY_VERSION, 'profile': 'full', 'specs': [],
                     'tested_revision': git('rev-parse', 'HEAD'), 'tested_tree': tree(),
                     'backend_fingerprint': backend_fingerprint(), 'reasons': ['Base unavailable: full gate']}
        value['detected_profile'] = value['profile']
        if git('diff', '--name-only') or git('diff', '--cached', '--name-only'):
            raise ValueError('Commit tracked changes before validation')
        evidence = ({'reuse': False, 'profile': 'full', 'specs': []} if args.full else
                    select_evidence(value, GitHub(args.repository), args.reuse_merged_pr))
        value.update(evidence)
        if args.full:
            value.update(profile='full', specs=[], reuse=False)
        # Reuse is valid only for the push to the production branch.
        if args.reuse_merged_pr and os.getenv('GITHUB_REF') != 'refs/heads/main':
            raise ValueError('Merged PR reuse is restricted to main')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value.get(key) for key in
                      ('profile', 'detected_profile', 'reuse', 'tested_tree', 'evidence_reason', 'source_run_id')}))
    if os.getenv('GITHUB_OUTPUT') and args.command == 'plan':
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            output.write(f'profile={value["profile"]}\nreuse={str(value.get("reuse", False)).lower()}\n')


if __name__ == '__main__':
    main()
