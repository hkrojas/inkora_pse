from __future__ import annotations

import argparse
import os
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from pruebas import run_backend_predeploy_check


def test_build_migrations_command_uses_dry_run():
    command = run_backend_predeploy_check.build_migrations_command()

    assert command[1:] == ["backend/run_launch_migrations.py", "--dry-run"]


def test_build_critical_command_supports_subset_and_flags():
    command = run_backend_predeploy_check.build_critical_command(
        selected_files=["test_auth.py", "test_cotizaciones.py"],
        verbose=True,
        maxfail=2,
    )

    assert command == [
        sys.executable,
        "pruebas/run_backend_critical_suite.py",
        "--files",
        "test_auth.py",
        "test_cotizaciones.py",
        "--verbose",
        "--maxfail",
        "2",
    ]


def test_build_beta_command_uses_smoke_defaults():
    command = run_backend_predeploy_check.build_beta_command(
        limit=1,
        start_index=1,
        families=run_backend_predeploy_check.DEFAULT_BETA_SMOKE_FAMILIES,
    )

    assert command == [
        sys.executable,
        "pruebas/run_backend_beta_suite.py",
        "--limit",
        "1",
        "--start-index",
        "1",
        "--families",
        "boleta",
        "factura",
        "nota_credito",
        "nota_debito",
        "baja_factura",
        "retencion",
        "percepcion",
        "reversion",
    ]


def test_build_steps_respects_skips():
    args = argparse.Namespace(
        skip_migrations=False,
        skip_critical=True,
        skip_beta=False,
        critical_files=None,
        critical_verbose=False,
        critical_maxfail=0,
        beta_limit=1,
        beta_start_index=3,
        beta_families=["factura"],
    )

    steps = run_backend_predeploy_check.build_steps(args)

    assert [label for label, _ in steps] == ["Migraciones dry-run", "Smoke beta real"]
    assert steps[1][1][-1] == "factura"
