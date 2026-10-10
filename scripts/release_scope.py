"""Conservative release scope. Unknown changes always require the full gate."""
from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
POLICY_VERSION = 1
SMOKE = {'navigation.spec.js', 'permissions.spec.js', 'topbar-mobile.spec.js'}
DOCUMENTS = {'fiscal-delivery.spec.js', 'operational-pagination.spec.js',
             'uniform-pagination.spec.js', 'comprobante-mobile-layout.spec.js'}
PAGE_SPECS = {
    'FacturasPage.jsx': DOCUMENTS,
    'BoletasPage.jsx': DOCUMENTS,
    'ClientesPage.jsx': {'clientes-directory.spec.js', 'uniform-pagination.spec.js'},
    'ProductosPage.jsx': {'uniform-pagination.spec.js'},
    'CobranzaPage.jsx': {'operational-pagination.spec.js', 'uniform-pagination.spec.js'},
    'Dashboard.jsx': {'dashboard-live-data.spec.js'},
    'DashboardMockup.jsx': {'dashboard-mockup.spec.js'},
    'LandingPage.jsx': {'landing.spec.js'},
}
COMPONENT_SPECS = {
    'frontend/src/components/documents/DocumentList.jsx': DOCUMENTS,
    'frontend/src/components/dashboard/DashboardEntityFilter.jsx': {'dashboard-live-data.spec.js'},
    'frontend/src/components/dashboard/DashboardExplorer.jsx': {'dashboard-live-data.spec.js'},
}
GLOBAL_FRONTEND = {
    'frontend/src/styles/globals.css', 'frontend/src/components/Sidebar.jsx',
    'frontend/src/components/ui/Modal.jsx', 'frontend/src/components/ui/Drawer.jsx',
    'frontend/src/components/ui/ActionMenu.jsx', 'frontend/src/components/ui/actionMenu.css',
    'frontend/src/components/ui/Pagination.jsx', 'frontend/src/components/ui/CustomSelect.jsx',
    'frontend/src/components/ui/DatePicker.jsx',
}


def git(*args, root=ROOT):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, encoding='utf-8').strip()


def revision(ref, root=ROOT):
    return git('rev-parse', '--verify', f'{ref}^{{commit}}', root=root)


def tree(ref='HEAD', root=ROOT):
    return git('rev-parse', f'{ref}^{{tree}}', root=root)


def backend_fingerprint(ref='HEAD', root=ROOT):
    # Include tests, dependencies and the gate itself, not just runtime files.
    entries = []
    for entry in git('ls-tree', '-r', ref, root=root).splitlines():
        path = entry.split('\t', 1)[1]
        if path.startswith(('frontend/src/', 'frontend/static/')):
            continue
        if path.startswith('docs/') and path.endswith('.md'):
            continue
        entries.append(entry)
    entries = '\n'.join(entries)
    return hashlib.sha256(entries.encode()).hexdigest()


def changes(base, head='HEAD', root=ROOT):
    base, head = revision(base, root), revision(head, root)
    subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', base, head], check=True)
    # Disable rename collapsing: both old and new paths must be classified.
    raw = git('diff', '--name-status', '--no-renames', base, head, root=root)
    return [(line.split('\t', 1)[0], line.split('\t', 1)[1])
            for line in raw.splitlines() if line]


def css_rules(text):
    """Read balanced CSS, preserving rule order and at-rule context.

    This is deliberately not a CSS optimizer. Unsupported nesting fails closed.
    """
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)

    def scan(value, context=()):
        result, start, depth, quote, escaped = [], 0, 0, None, False
        header = None
        for i, char in enumerate(value):
            if escaped:
                escaped = False
                continue
            if char == '\\':
                escaped = True
                continue
            if quote:
                if char == quote:
                    quote = None
                continue
            if char in "\"'":
                quote = char
            elif char == ';' and depth == 0:
                statement = value[start:i + 1].strip()
                if statement:
                    result.append((context, statement, ''))
                start = i + 1
            elif char == '{':
                if depth == 0:
                    header, body_start = value[start:i].strip(), i + 1
                depth += 1
            elif char == '}':
                depth -= 1
                if depth < 0:
                    raise ValueError('CSS unbalanced')
                if depth == 0:
                    body = value[body_start:i].strip()
                    if header.startswith('@'):
                        result.extend(scan(body, context + (header,)))
                    else:
                        if '{' in body or '}' in body:
                            raise ValueError('Nested CSS requires broad coverage')
                        result.append((context, header, body))
                    start = i + 1
        if depth or quote or value[start:].strip():
            raise ValueError('CSS unsupported')
        return result

    return scan(text)


def document_only_css(before, after):
    try:
        left, right = css_rules(before), css_rules(after)
        changed = []
        for tag, a, b, c, d in difflib.SequenceMatcher(a=left, b=right, autojunk=False).get_opcodes():
            if tag != 'equal':
                changed.extend(left[a:b] + right[c:d])
        if not changed:
            return True
        for context, selector, body in changed:
            if not body or any(not x.startswith(('@media ', '@container ', '@supports ')) for x in context):
                return False
            for part in selector.split(','):
                if not re.match(r'^\.document-list-table(?:$|\s|[.#:\[])', part.strip()):
                    return False
                if any(symbol in part for symbol in ('+', '~', ':has(', ':global(')):
                    return False
        return True
    except ValueError:
        return False


def classify(entries, read_css=None):
    entries = list(entries)
    if not entries:
        return {'profile': 'full', 'specs': [], 'reasons': ['Empty diff cannot establish a documentation-only release']}
    if any(status != 'M' for status, _ in entries):
        return {'profile': 'full', 'specs': [], 'reasons': ['Added, deleted or renamed paths require full validation']}
    specs, reasons, profile = set(SMOKE), [], 'visual'
    runtime = False
    for status, path in entries:
        if status != 'M':
            return {'profile': 'full', 'specs': [], 'reasons': [f'{status} {path}: addition/deletion requires full validation']}
        if path.startswith('docs/') and path.endswith('.md'):
            continue
        runtime = True
        if path == 'frontend/src/styles/globals.css':
            if read_css and document_only_css(*read_css(path)):
                specs.update(DOCUMENTS)
                reasons.append('CSS scoped to document tables')
            else:
                profile, specs = 'frontend', set()
                reasons.append('Global CSS: all browser flows')
                # An empty spec list means all; preserve that below.
                break
        elif path in COMPONENT_SPECS:
            specs.update(COMPONENT_SPECS[path])
            profile = 'frontend'
        elif path.startswith('frontend/src/pages/') and Path(path).name in PAGE_SPECS:
            specs.update(PAGE_SPECS[Path(path).name])
            profile = 'frontend'
        elif path in GLOBAL_FRONTEND:
            profile, specs = 'frontend', set()
            reasons.append('Shared frontend: all browser flows')
            break
        else:
            return {'profile': 'full', 'specs': [], 'reasons': [f'{path}: sensitive or unmapped path']}
    # Even when broad frontend coverage was selected, inspect every path for backend/unknown changes.
    allowed = set(COMPONENT_SPECS) | GLOBAL_FRONTEND
    for _, path in entries:
        if not (path in allowed or (path.startswith('docs/') and path.endswith('.md')) or
                (path.startswith('frontend/src/pages/') and Path(path).name in PAGE_SPECS)):
            return {'profile': 'full', 'specs': [], 'reasons': [f'{path}: sensitive or unmapped path']}
    if not runtime:
        profile, specs = 'docs', set()
    return {'profile': profile, 'specs': sorted(specs), 'reasons': reasons or ['Explicit section-to-test mapping']}


def plan(base, head='HEAD', root=ROOT):
    base, head = revision(base, root), revision(head, root)
    entries = changes(base, head, root)
    selection = classify(entries, lambda path: (
        git('show', f'{base}:{path}', root=root), git('show', f'{head}:{path}', root=root)))
    return {'policy_version': POLICY_VERSION, 'base_revision': base,
            'tested_revision': head, 'tested_tree': tree(head, root),
            'backend_fingerprint': backend_fingerprint(head, root),
            'changes': [{'status': status, 'path': path} for status, path in entries],
            **selection}
