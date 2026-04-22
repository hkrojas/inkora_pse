from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BETA_SMOKE_FAMILIES = [
    "boleta",
    "factura",
    "nota_credito",
    "nota_debito",
    "baja_factura",
    "retencion",
    "percepcion",
    "reversion",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta la puerta predeploy del backend: migraciones dry-run, "
            "suite critica y smoke real ApisPeru Beta."
        )
    )
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Omite el dry-run de migraciones.",
    )
    parser.add_argument(
        "--skip-critical",
        action="store_true",
        help="Omite la suite critica de backend.",
    )
    parser.add_argument(
        "--skip-beta",
        action="store_true",
        help="Omite la smoke real contra ApisPeru Beta.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra los comandos sin ejecutarlos.",
    )
    parser.add_argument(
        "--critical-files",
        nargs="*",
        help="Subset opcional de archivos de la suite critica.",
    )
    parser.add_argument(
        "--critical-verbose",
        action="store_true",
        help="Usa salida verbose al correr la suite critica.",
    )
    parser.add_argument(
        "--critical-maxfail",
        type=int,
        default=0,
        help="Detiene la suite critica tras N fallos (0 = sin limite).",
    )
    parser.add_argument(
        "--beta-limit",
        type=int,
        default=1,
        help="Numero de casos por familia para la smoke beta.",
    )
    parser.add_argument(
        "--beta-start-index",
        type=int,
        default=1,
        help="Indice inicial 1-based para la smoke beta.",
    )
    parser.add_argument(
        "--beta-families",
        nargs="*",
        default=list(DEFAULT_BETA_SMOKE_FAMILIES),
        help="Familias a ejecutar en la smoke beta.",
    )
    return parser.parse_args()


def build_migrations_command() -> list[str]:
    return [sys.executable, "backend/run_launch_migrations.py", "--dry-run"]


def build_critical_command(
    *,
    selected_files: list[str] | None,
    verbose: bool,
    maxfail: int,
) -> list[str]:
    command = [sys.executable, "pruebas/run_backend_critical_suite.py"]
    if selected_files:
        command.extend(["--files", *selected_files])
    if verbose:
        command.append("--verbose")
    if maxfail > 0:
        command.extend(["--maxfail", str(maxfail)])
    return command


def build_beta_command(
    *,
    limit: int,
    start_index: int,
    families: list[str],
) -> list[str]:
    return [
        sys.executable,
        "pruebas/run_backend_beta_suite.py",
        "--limit",
        str(limit),
        "--start-index",
        str(start_index),
        "--families",
        *families,
    ]


def build_steps(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    steps: list[tuple[str, list[str]]] = []
    if not args.skip_migrations:
        steps.append(("Migraciones dry-run", build_migrations_command()))
    if not args.skip_critical:
        steps.append(
            (
                "Suite critica",
                build_critical_command(
                    selected_files=args.critical_files,
                    verbose=args.critical_verbose,
                    maxfail=args.critical_maxfail,
                ),
            )
        )
    if not args.skip_beta:
        steps.append(
            (
                "Smoke beta real",
                build_beta_command(
                    limit=args.beta_limit,
                    start_index=args.beta_start_index,
                    families=args.beta_families,
                ),
            )
        )
    return steps


def run_steps(steps: list[tuple[str, list[str]]], *, dry_run: bool) -> int:
    if not steps:
        print("[predeploy] No hay pasos para ejecutar.")
        return 0

    for index, (label, command) in enumerate(steps, start=1):
        print(f"[predeploy] Paso {index}: {label}")
        print(f"[predeploy] Comando: {' '.join(command)}")
        if dry_run:
            continue

        completed = subprocess.run(command, cwd=ROOT_DIR)
        if completed.returncode != 0:
            print(f"[predeploy] FALLO en '{label}' con exit code {completed.returncode}")
            return completed.returncode

    print("[predeploy] OK")
    return 0


def main() -> int:
    args = parse_args()
    steps = build_steps(args)
    return run_steps(steps, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
