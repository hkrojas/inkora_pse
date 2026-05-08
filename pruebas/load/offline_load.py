"""Carga controlada offline para Inkora PSE.

No emite documentos fiscales ni llama Smart PSE/SUNAT. Mide login, lecturas
paginadas y, opcionalmente, solicitud de PDF existente/generado en background.
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass

import httpx


READ_PATHS = [
    "/analytics/dashboard",
    "/tenant/",
    "/clientes/page?skip=0&limit=15",
    "/productos/page?skip=0&limit=15",
    "/guias-remision/?skip=0&limit=15",
]


@dataclass
class Sample:
    name: str
    status_code: int
    duration_ms: float
    error: str | None = None


def percentile(values: list[float], percent: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((percent / 100) * (len(ordered) - 1)))
    return ordered[index]


async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/token",
        data={"username": email, "password": password},
        timeout=10,
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return token


async def measure_get(client: httpx.AsyncClient, path: str, name: str) -> Sample:
    started = time.perf_counter()
    try:
        response = await client.get(path, timeout=15)
        duration_ms = (time.perf_counter() - started) * 1000
        return Sample(name=name, status_code=response.status_code, duration_ms=duration_ms)
    except Exception as exc:  # noqa: BLE001 - load script must record all failures.
        duration_ms = (time.perf_counter() - started) * 1000
        return Sample(name=name, status_code=0, duration_ms=duration_ms, error=type(exc).__name__)


async def run_worker(args, worker_id: int) -> list[Sample]:
    async with httpx.AsyncClient(base_url=args.base_url.rstrip("/")) as client:
        samples: list[Sample] = []
        started = time.perf_counter()
        try:
            await login(client, args.email, args.password)
            samples.append(Sample("login", 200, (time.perf_counter() - started) * 1000))
        except Exception as exc:  # noqa: BLE001
            samples.append(Sample("login", 0, (time.perf_counter() - started) * 1000, type(exc).__name__))
            return samples

        for _ in range(args.iterations):
            for path in READ_PATHS:
                samples.append(await measure_get(client, path, path))
            if args.pdf_cotizacion_id:
                samples.append(
                    await measure_get(
                        client,
                        f"/cotizaciones/{args.pdf_cotizacion_id}/pdf?redirect=false",
                        "pdf",
                    )
                )
            await asyncio.sleep(args.pause)
        return samples


def print_summary(samples: list[Sample]) -> None:
    by_name: dict[str, list[Sample]] = {}
    for sample in samples:
        by_name.setdefault(sample.name, []).append(sample)

    for name, group in sorted(by_name.items()):
        durations = [sample.duration_ms for sample in group]
        errors = [sample for sample in group if sample.status_code >= 500 or sample.status_code == 0]
        print(
            f"{name:38} count={len(group):4} "
            f"p50={statistics.median(durations):8.2f}ms "
            f"p95={percentile(durations, 95):8.2f}ms "
            f"max={max(durations):8.2f}ms "
            f"5xx/errors={len(errors):3}"
        )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--pause", type=float, default=0.1)
    parser.add_argument("--pdf-cotizacion-id", type=int)
    args = parser.parse_args()

    results = await asyncio.gather(
        *(run_worker(args, worker_id) for worker_id in range(args.concurrency))
    )
    samples = [sample for group in results for sample in group]
    print_summary(samples)


if __name__ == "__main__":
    asyncio.run(main())
