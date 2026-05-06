from __future__ import annotations

import ast
from pathlib import Path

from alembic.config import Config


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
ALEMBIC_ENV = BACKEND_DIR / "alembic" / "env.py"
BASELINE_REVISION = (
    BACKEND_DIR
    / "alembic"
    / "versions"
    / "0001_prebeta_baseline.py"
)
BETA_FLAGS_REVISION = (
    BACKEND_DIR
    / "alembic"
    / "versions"
    / "0002_beta_feature_flags.py"
)


def _parse_baseline():
    return ast.parse(BASELINE_REVISION.read_text(encoding="utf-8"))


def _assigned_string(module: ast.Module, name: str):
    for node in module.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                if isinstance(node.value, ast.Constant):
                    return node.value.value
    raise AssertionError(f"No se encontro asignacion {name!r}")


def _function_body(module: ast.Module, name: str):
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node.body
    raise AssertionError(f"No se encontro funcion {name!r}")


def test_alembic_baseline_files_exist():
    assert ALEMBIC_INI.exists()
    assert ALEMBIC_ENV.exists()
    assert BASELINE_REVISION.exists()
    assert BETA_FLAGS_REVISION.exists()


def test_baseline_revision_has_no_parent():
    module = _parse_baseline()

    assert _assigned_string(module, "revision") == "0001_prebeta_baseline"
    assert _assigned_string(module, "down_revision") is None


def test_baseline_upgrade_and_downgrade_are_noop():
    module = _parse_baseline()

    for function_name in ("upgrade", "downgrade"):
        body = _function_body(module, function_name)
        assert len(body) == 1
        assert isinstance(body[0], ast.Pass)


def test_baseline_revision_does_not_import_alembic_operations():
    content = BASELINE_REVISION.read_text(encoding="utf-8")

    forbidden_tokens = (
        "op.create_table",
        "op.drop_table",
        "op.add_column",
        "op.drop_column",
        "op.execute",
        "create_index",
        "drop_index",
    )
    assert not any(token in content for token in forbidden_tokens)


def test_alembic_config_loads_without_running_migrations():
    config = Config(str(ALEMBIC_INI))

    assert config.get_main_option("script_location").endswith("backend/alembic")
    assert config.get_main_option("prepend_sys_path").endswith("backend")


def test_beta_feature_flags_revision_depends_on_baseline_and_adds_subscription_column():
    module = ast.parse(BETA_FLAGS_REVISION.read_text(encoding="utf-8"))

    assert _assigned_string(module, "revision") == "0002_beta_feature_flags"
    assert _assigned_string(module, "down_revision") == "0001_prebeta_baseline"

    content = BETA_FLAGS_REVISION.read_text(encoding="utf-8")
    assert "op.add_column" in content
    assert '"subscriptions"' in content
    assert '"beta_feature_flags"' in content


def test_env_has_autogenerate_filter_for_frozen_tables():
    content = ALEMBIC_ENV.read_text(encoding="utf-8")

    assert "FROZEN_TABLES" in content
    assert "include_object" in content
    assert "recetas_bom" in content
    assert "ordenes_produccion" in content
