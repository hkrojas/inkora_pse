"""Run Inkora E2E against an isolated local backend and disposable SQLite DB.

The runner never accepts remote base URLs, production credentials, Supabase or
fiscal-provider tokens. It starts only ports 8000 and 5173 and removes the
temporary database and Playwright authentication state on exit.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
AUTH_STATE = FRONTEND / ".playwright" / ".auth" / "tenant.json"
TENANT_EMAIL = "admin@demo.inkora.pe"


def _require_available_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"El puerto local {port} ya está ocupado.") from exc


def _wait_for_backend(process: subprocess.Popen, timeout_seconds: int = 45) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("El backend E2E terminó antes de responder /health.")
        try:
            with urlopen("http://127.0.0.1:8000/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError("El backend E2E no respondió /health dentro del plazo.")


def _remove_auth_state() -> None:
    if AUTH_STATE.is_file():
        AUTH_STATE.unlink()
    for directory in (AUTH_STATE.parent, AUTH_STATE.parent.parent):
        try:
            directory.rmdir()
        except (FileNotFoundError, OSError):
            pass


def _tail(path: Path, lines: int = 80) -> str:
    if not path.is_file():
        return ""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])


@contextmanager
def _temporary_directory():
    temp_dir = Path(tempfile.mkdtemp(prefix="inkora_e2e_"))
    try:
        yield temp_dir
    finally:
        for attempt in range(10):
            try:
                shutil.rmtree(temp_dir)
                break
            except FileNotFoundError:
                break
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(0.25)


def main() -> int:
    if os.getenv("E2E_BASE_URL") or os.getenv("E2E_ALLOW_REMOTE"):
        raise RuntimeError("El runner local rechaza E2E_BASE_URL y E2E_ALLOW_REMOTE.")
    npx = shutil.which("npx.cmd" if os.name == "nt" else "npx")
    if not npx:
        raise RuntimeError("No se encontró npx; instala Node.js/npm antes de ejecutar E2E.")

    _require_available_port(8000)
    _require_available_port(5173)
    _remove_auth_state()

    password = secrets.token_urlsafe(24)
    backend_process = None
    with _temporary_directory() as temp_dir:
        database_path = temp_dir / "inkora_e2e.db"
        backend_log_path = temp_dir / "backend.log"
        environment = os.environ.copy()
        environment.update({
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "SECRET_KEY": secrets.token_urlsafe(48),
            "ENVIRONMENT": "test",
            "FISCAL_ENV": "beta",
            "INIT_DB_ON_STARTUP": "false",
            "API_TOKEN": "",
            "SMARTPSE_API_TOKEN": "",
            "DNIRUC_TOKEN": "",
            "SUPABASE_URL": "",
            "SUPABASE_KEY": "",
            "SUPABASE_SERVICE_ROLE_KEY": "",
            "BACKEND_URL": "http://127.0.0.1:8000",
            "CORS_ALLOW_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173",
            "EMISSION_MODE_DEFAULT": "async",
            "INKORA_DEMO_ADMIN_EMAIL": TENANT_EMAIL,
            "INKORA_DEMO_ADMIN_PASSWORD": password,
            "E2E_TENANT_EMAIL": TENANT_EMAIL,
            "E2E_TENANT_PASSWORD": password,
            "E2E_API_URL": "http://127.0.0.1:8000",
            "E2E_WORKERS": "1",
        })
        for key in ("E2E_BASE_URL", "E2E_ALLOW_REMOTE", "E2E_ISOLATED"):
            environment.pop(key, None)

        subprocess.run(
            [sys.executable, "seed_demo_tenant.py"],
            cwd=BACKEND,
            env=environment,
            check=True,
        )

        exchange_rate = {
            "source": "synthetic-e2e",
            "source_url": "local://e2e",
            "date": date.today().isoformat(),
            "buy": "3.700",
            "sell": "3.710",
            "fetched_at": f"{date.today().isoformat()}T00:00:00+00:00",
            "status": "ok",
            "stale": False,
        }
        bootstrap = (
            "import services.sunat_exchange_rate_service as service;"
            f"service._set_cached_value({exchange_rate!r});"
            "import uvicorn;"
            "uvicorn.run('main:app', host='127.0.0.1', port=8000, log_level='warning')"
        )

        try:
            with backend_log_path.open("w", encoding="utf-8") as backend_log:
                backend_process = subprocess.Popen(
                    [sys.executable, "-c", bootstrap],
                    cwd=BACKEND,
                    env=environment,
                    stdout=backend_log,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                _wait_for_backend(backend_process)
                completed = subprocess.run(
                    [npx, "playwright", "test"],
                    cwd=FRONTEND,
                    env=environment,
                )
                return completed.returncode
        except Exception:
            try:
                backend_log.flush()
            except (NameError, OSError):
                pass
            backend_tail = _tail(backend_log_path)
            if backend_tail:
                print("--- backend E2E (últimas líneas) ---", file=sys.stderr)
                print(backend_tail, file=sys.stderr)
            raise
        finally:
            if backend_process is not None and backend_process.poll() is None:
                backend_process.terminate()
                try:
                    backend_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    backend_process.kill()
                    backend_process.wait(timeout=5)
            _remove_auth_state()


if __name__ == "__main__":
    raise SystemExit(main())
