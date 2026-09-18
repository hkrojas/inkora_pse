"""Public, non-secret identity embedded by the immutable release packager."""
import json
from pathlib import Path


def release_identity():
    try:
        value = json.loads((Path(__file__).resolve().parents[1] / 'release.json').read_text(encoding='utf-8'))
        return {key: value[key] for key in ('base_revision', 'content_sha256')}
    except (OSError, ValueError, KeyError, TypeError):
        return {'base_revision': None, 'content_sha256': None}
