from importlib import metadata
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


BACKEND = Path(__file__).resolve().parent
LOCK_FILES = (BACKEND / "requirements-lock.txt", BACKEND / "requirements-test.txt")


def _declared_requirements(path):
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-r ")):
            continue
        yield Requirement(line)


def test_dependency_locks_pin_the_complete_installed_runtime_and_test_closure():
    declared = [requirement for path in LOCK_FILES for requirement in _declared_requirements(path)]
    pinned = {canonicalize_name(requirement.name) for requirement in declared}
    unpinned = [str(requirement) for requirement in declared if not requirement.specifier]
    missing = set()
    visited = set()
    queue = [(canonicalize_name(requirement.name), frozenset(requirement.extras)) for requirement in declared]

    while queue:
        name, extras = queue.pop()
        visit_key = (name, extras)
        if visit_key in visited:
            continue
        visited.add(visit_key)
        distribution = metadata.distribution(name)
        for raw_requirement in distribution.requires or ():
            requirement = Requirement(raw_requirement)
            environments = [default_environment()]
            environments.extend(default_environment() | {"extra": extra} for extra in extras)
            if requirement.marker and not any(requirement.marker.evaluate(env) for env in environments):
                continue
            dependency_name = canonicalize_name(requirement.name)
            if dependency_name not in pinned:
                missing.add(dependency_name)
            queue.append((dependency_name, frozenset(requirement.extras)))

    assert not unpinned, f"Dependencias sin versión exacta: {unpinned}"
    assert not missing, f"Dependencias transitivas sin fijar: {sorted(missing)}"
