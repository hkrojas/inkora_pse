"""
test_concurrent_billing.py — Prueba de carga real para facturación simultánea.

Simula N usuarios emitiendo facturas al mismo tiempo contra un backend real.
Mide:
  - Tiempo promedio de respuesta
  - Tasa de éxito (200/202 vs errores)
  - Degradación progresiva

Uso:
  # Configurar tu .env con DATABASE_URL apuntando a tu BD real
  python test_concurrent_billing.py --users 20 --ramp-seconds 5

  # Prueba rápida con 10 usuarios
  python test_concurrent_billing.py --users 10

Requisitos:
  pip install requests concurrent.futures statistics
"""
import argparse
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

# ── Configuración ────────────────────────────────────────────────────────────

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
EMAIL_ADMIN = os.getenv("TEST_EMAIL", "admin@printflow.com")
PASSWORD = os.getenv("TEST_PASSWORD", "admin123")
TENANT_RUC = os.getenv("TEST_TENANT_RUC")  # Opcional: para filtrar datos de prueba


# ── Helpers de API ───────────────────────────────────────────────────────────

def login(email: str, password: str) -> str:
    """Login y retorno del token JWT."""
    resp = requests.post(
        f"{BASE_URL}/token",
        data={
            "username": email,
            "password": password,
            "grant_type": "password",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed: {resp.status_code} {resp.text[:200]}")
    return resp.json()["access_token"]


def get_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def find_cliente(token: str) -> dict:
    """Busca un cliente existente del tenant."""
    resp = requests.get(f"{BASE_URL}/clientes/?limit=1", headers=get_headers(token), timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"GET /clientes failed: {resp.status_code}")
    clientes = resp.json()
    if not clientes:
        raise RuntimeError("No hay clientes en el tenant. Crea al menos uno antes de probar.")
    return clientes[0]


def find_cotizacion_pendiente(token: str) -> dict | None:
    """Busca una cotización pendiente con items."""
    resp = requests.get(f"{BASE_URL}/cotizaciones/?limit=50", headers=get_headers(token), timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"GET /cotizaciones failed: {resp.status_code}")
    cotizaciones = resp.json()
    for cot in cotizaciones:
        if cot.get("estado") == "pendiente" and cot.get("document_kind") == "quotation":
            # Verificar que tiene items
            items_resp = requests.get(
                f"{BASE_URL}/cotizaciones/{cot['id']}",
                headers=get_headers(token),
                timeout=10,
            )
            if items_resp.status_code == 200:
                data = items_resp.json()
                if data.get("items"):
                    return data
    return None


def crear_cotizacion_de_prueba(token: str, cliente_id: int) -> dict:
    """Crea una cotización de prueba con un item."""
    payload = {
        "cliente_id": cliente_id,
        "moneda": "PEN",
        "tipo_comprobante": "00",
        "items": [
            {
                "descripcion": f"Servicio de prueba {datetime.now().strftime('%H%M%S%f')}",
                "cantidad": 1,
                "precio_unitario": 118.00,
            }
        ],
    }
    resp = requests.post(
        f"{BASE_URL}/cotizaciones/",
        headers=get_headers(token),
        json=payload,
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"POST /cotizaciones failed: {resp.status_code} {resp.text[:200]}")
    return resp.json()


def emitir_factura_sync(token: str, cotizacion_id: int) -> dict:
    """Emite una factura en modo síncrono (bloqueante)."""
    payload = {"tipo_comprobante": "03"}  # Boleta para pruebas
    resp = requests.post(
        f"{BASE_URL}/cotizaciones/{cotizacion_id}/facturar",
        headers=get_headers(token),
        json=payload,
        timeout=60,  # La factura síncrona puede tardar 10-30s
    )
    return {
        "status_code": resp.status_code,
        "response": resp.json() if resp.status_code < 500 else resp.text[:500],
        "elapsed_ms": resp.elapsed.total_seconds() * 1000,
    }


def emitir_factura_async(token: str, cotizacion_id: int) -> dict:
    """Emite una factura en modo asíncrono (encolado)."""
    payload = {"tipo_comprobante": "03"}
    resp = requests.post(
        f"{BASE_URL}/cotizaciones/{cotizacion_id}/facturar?mode=async",
        headers=get_headers(token),
        json=payload,
        timeout=15,
    )
    return {
        "status_code": resp.status_code,
        "response": resp.json() if resp.status_code < 500 else resp.text[:500],
        "elapsed_ms": resp.elapsed.total_seconds() * 1000,
    }


# ── Worker de un usuario simulado ────────────────────────────────────────────

def simulate_user(
    user_index: int,
    token: str,
    cotizacion_id: int,
    mode: str,
) -> dict:
    """Simula un usuario facturando una vez."""
    emit_fn = emitir_factura_async if mode == "async" else emitir_factura_sync
    try:
        result = emit_fn(token, cotizacion_id)
        return {
            "user": user_index,
            "success": result["status_code"] in (200, 202),
            "status_code": result["status_code"],
            "elapsed_ms": result["elapsed_ms"],
            "error": None,
        }
    except Exception as exc:
        return {
            "user": user_index,
            "success": False,
            "status_code": 0,
            "elapsed_ms": 0,
            "error": str(exc)[:200],
        }


# ── Test Runner ──────────────────────────────────────────────────────────────

def run_load_test(
    num_users: int,
    mode: str = "async",
    ramp_seconds: int = 0,
    repeat_per_user: int = 1,
):
    """
    Ejecuta la prueba de carga.

    Args:
        num_users: Cuántos usuarios simultáneos simular.
        mode: 'sync' o 'async'.
        ramp_seconds: Si > 0, lanza los usuarios escalonados en este tiempo.
        repeat_per_user: Cuántas facturas emite cada usuario.
    """
    print("=" * 70)
    print(f"  PRUEBA DE CARGA — Facturación Simultánea")
    print("=" * 70)
    print(f"  Backend:     {BASE_URL}")
    print(f"  Usuarios:    {num_users}")
    print(f"  Modo:        {mode}")
    print(f"  Repeticiones: {repeat_per_user} por usuario")
    print(f"  Ramp:        {ramp_seconds}s")
    print(f"  Fecha:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ── Paso 1: Login ─────────────────────────────────────────────────────
    print("\n[1/4] Autenticando...")
    try:
        token = login(EMAIL_ADMIN, PASSWORD)
        print(f"  ✅ Login exitoso")
    except Exception as exc:
        print(f"  ❌ Login fallido: {exc}")
        sys.exit(1)

    # ── Paso 2: Preparar datos ────────────────────────────────────────────
    print("\n[2/4] Preparando datos de prueba...")
    try:
        cliente = find_cliente(token)
        print(f"  ✅ Cliente encontrado: {cliente.get('razon_social', 'N/A')} (id={cliente['id']})")
    except Exception as exc:
        print(f"  ❌ Error buscando cliente: {exc}")
        sys.exit(1)

    # Crear cotizaciones de prueba
    cotizaciones = []
    print(f"\n  Creando {num_users * repeat_per_user} cotizaciones de prueba...")
    for i in range(num_users * repeat_per_user):
        try:
            cot = crear_cotizacion_de_prueba(token, cliente["id"])
            cotizaciones.append(cot)
            if (i + 1) % 10 == 0 or i == 0:
                print(f"    {i + 1}/{num_users * repeat_per_user} creadas...")
        except Exception as exc:
            print(f"    ❌ Error creando cotización {i}: {exc}")
    print(f"  ✅ {len(cotizaciones)} cotizaciones listas")

    # ── Paso 3: Ejecutar prueba ───────────────────────────────────────────
    print(f"\n[3/4] Ejecutando prueba — {num_users} usuarios × {repeat_per_user} facturas...")
    results = []
    all_results = []
    total_requests = num_users * repeat_per_user
    started_at = time.time()

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = {}
        for user_idx in range(num_users):
            for rep in range(repeat_per_user):
                cot_idx = user_idx * repeat_per_user + rep
                if cot_idx < len(cotizaciones):
                    cot_id = cotizaciones[cot_idx]["id"]
                    future = executor.submit(
                        simulate_user,
                        user_idx,
                        token,
                        cot_id,
                        mode,
                    )
                    futures[future] = (user_idx, rep)

                    # Ramp: escalonar el lanzamiento
                    if ramp_seconds > 0:
                        time.sleep(ramp_seconds / total_requests)

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    total_time = time.time() - started_at

    # ── Paso 4: Reporte ───────────────────────────────────────────────────
    print(f"\n[4/4] Resultados")
    print("-" * 70)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    latencies = [r["elapsed_ms"] for r in results if r["elapsed_ms"] > 0]

    # Desglose por status code
    status_counts = {}
    for r in results:
        code = r["status_code"]
        status_counts[code] = status_counts.get(code, 0) + 1

    print(f"\n  Tiempo total:       {total_time:.1f}s")
    print(f"  Total requests:     {total_requests}")
    print(f"  Exitosos:           {len(successful)} ({len(successful)/total_requests*100:.0f}%)")
    print(f"  Fallidos:           {len(failed)} ({len(failed)/total_requests*100:.0f}%)")

    if status_counts:
        print(f"\n  Status codes:")
        for code, count in sorted(status_counts.items()):
            print(f"    {code}: {count}")

    if latencies:
        print(f"\n  Latencia (ms):")
        print(f"    Mínimo:     {min(latencies):.0f}")
        print(f"    P50:        {statistics.median(latencies):.0f}")
        print(f"    P90:        {sorted(latencies)[int(len(latencies) * 0.9)]:.0f}")
        print(f"    P99:        {sorted(latencies)[int(len(latencies) * 0.99)]:.0f}")
        print(f"    Máximo:     {max(latencies):.0f}")
        print(f"    Promedio:   {statistics.mean(latencies):.0f}")

    # Facturas por segundo
    rps = total_requests / total_time if total_time > 0 else 0
    print(f"\n  Throughput:         {rps:.1f} facturas/segundo")

    # Errores detallados
    if failed:
        print(f"\n  Errores:")
        for f_item in failed[:5]:
            print(f"    Usuario {f_item['user']}: {f_item['error'] or f'HTTP {f_item["status_code"]}'}")
        if len(failed) > 5:
            print(f"    ... y {len(failed) - 5} más")

    # Veredicto
    print("\n" + "=" * 70)
    if len(successful) == total_requests:
        verdict = "✅ TODAS EXITOSAS — El sistema soporta esta carga"
    elif len(successful) / total_requests >= 0.9:
        verdict = "⚠️  MAYORÍA EXITOSA — Degradación leve, revisar latencia P99"
    elif len(successful) / total_requests >= 0.5:
        verdict = "🟠 DEGRADADO — Más del 50% fallan o tardan demasiado"
    else:
        verdict = "❌ COLAPSADO — El sistema no soporta esta carga"

    print(f"  VEREDICTO: {verdict}")
    print("=" * 70)

    # Guardar resultados en JSON
    report = {
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "num_users": num_users,
        "mode": mode,
        "repeat_per_user": repeat_per_user,
        "ramp_seconds": ramp_seconds,
        "total_time_s": round(total_time, 2),
        "total_requests": total_requests,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate_pct": round(len(successful) / total_requests * 100, 1),
        "status_codes": status_counts,
        "latency_ms": {
            "min": round(min(latencies), 0) if latencies else 0,
            "p50": round(statistics.median(latencies), 0) if latencies else 0,
            "p90": round(sorted(latencies)[int(len(latencies) * 0.9)], 0) if latencies else 0,
            "p99": round(sorted(latencies)[int(len(latencies) * 0.99)], 0) if len(latencies) > 1 else 0,
            "max": round(max(latencies), 0) if latencies else 0,
            "avg": round(statistics.mean(latencies), 0) if latencies else 0,
        },
        "throughput_rps": round(rps, 2),
        "errors": [
            {"user": f["user"], "status_code": f["status_code"], "error": f["error"]}
            for f in failed[:20]
        ],
    }

    os.makedirs("pruebas", exist_ok=True)
    filename = f"pruebas/load_test_{mode}_{num_users}users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  📄 Reporte guardado: {filename}")

    return report


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prueba de carga para facturación simultánea")
    parser.add_argument("--users", type=int, default=10, help="Número de usuarios simultáneos")
    parser.add_argument("--mode", choices=["sync", "async"], default="async", help="Modo de emisión")
    parser.add_argument("--ramp", type=int, default=0, help="Segundos de ramp-up escalonado")
    parser.add_argument("--repeat", type=int, default=1, help="Facturas por usuario")
    args = parser.parse_args()

    run_load_test(
        num_users=args.users,
        mode=args.mode,
        ramp_seconds=args.ramp,
        repeat_per_user=args.repeat,
    )
