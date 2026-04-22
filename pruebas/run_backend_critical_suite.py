from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

CRITICAL_TEST_FILES = [
    "backend/test_auth.py",
    "backend/test_tenant_access_hardening.py",
    "backend/test_cotizaciones.py",
    "backend/test_payments.py",
    "backend/test_document_flow_transition.py",
    "backend/test_facturacion_guards.py",
    "backend/test_facturacion_fiscal.py",
    "backend/test_facturacion_comprobante_builder.py",
    "backend/test_apisperu_documentos_matrix.py",
    "backend/test_apisperu_payload_contracts.py",
    "backend/test_guias.py",
    "backend/test_guias_router.py",
    "backend/test_pdf_generator.py",
    "backend/test_predeploy_check.py",
]

CRITICAL_TEST_MAP = {Path(path).name: path for path in CRITICAL_TEST_FILES}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta la suite critica del backend Inkora sin depender de recordar archivos sueltos."
    )
    parser.add_argument(
        "--files",
        nargs="*",
        choices=sorted(CRITICAL_TEST_MAP),
        help="Subset de archivos de la suite critica a ejecutar.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Usa salida verbose de pytest.",
    )
    parser.add_argument(
        "--maxfail",
        type=int,
        default=0,
        help="Detiene la ejecucion tras N fallos (0 = sin limite).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el comando final sin ejecutarlo.",
    )
    return parser.parse_args()


def resolve_test_files(selected: list[str] | None) -> list[str]:
    if not selected:
        return list(CRITICAL_TEST_FILES)
    return [CRITICAL_TEST_MAP[name] for name in selected]


def build_pytest_command(test_files: list[str], *, verbose: bool, maxfail: int) -> list[str]:
    command = [sys.executable, "-m", "pytest", *test_files]
    command.append("-v" if verbose else "-q")
    if maxfail > 0:
        command.extend(["--maxfail", str(maxfail)])
    return command


def main() -> int:
    args = parse_args()
    test_files = resolve_test_files(args.files)
    command = build_pytest_command(
        test_files,
        verbose=args.verbose,
        maxfail=args.maxfail,
    )

    print("Suite critica backend:")
    for path in test_files:
        print(f" - {path}")
    print("Comando:")
    print(" ".join(command))

    if args.dry_run:
        return 0

    completed = subprocess.run(command, cwd=ROOT_DIR)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
