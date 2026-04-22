from __future__ import annotations

import argparse
import subprocess
import sys

from launch_migrations import iter_launch_migration_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta en orden la cadena canónica de migraciones launch/staging."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el orden de ejecución sin correr scripts.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Falla si falta algún script esperado.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exit_code = 0

    print("[migrations] Launch chain:")
    for script_path in iter_launch_migration_paths():
        if not script_path.exists():
            message = f"[migrations] SKIP: {script_path.name} no encontrado"
            if args.strict:
                print(message)
                return 1
            print(message)
            continue

        print(f"[migrations] {script_path.name}")
        if args.dry_run:
            continue

        completed = subprocess.run([sys.executable, str(script_path)], cwd=script_path.parent)
        if completed.returncode != 0:
            exit_code = completed.returncode
            break

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
