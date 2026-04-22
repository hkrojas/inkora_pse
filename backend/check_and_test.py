"""check_and_test.py — Verifica datos y corre prueba de carga"""
import requests
import json
import sys
import time
import os

BASE = "http://127.0.0.1:8000"
EMAIL = "admin@demo.inkora.pe"
PASSWORD = "demo1234"

def get_token():
    r = requests.post(f"{BASE}/token", data={
        "username": EMAIL, "password": PASSWORD, "grant_type": "password"
    }, timeout=10)
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    return r.json()["access_token"]

def get_headers(token):
    return {"Authorization": f"Bearer {token}"}

def count_pending_quotes(token):
    r = requests.get(f"{BASE}/cotizaciones/?limit=200", headers=get_headers(token), timeout=10)
    quotes = r.json()
    pending = [q for q in quotes if q["estado"] == "pendiente" and q["document_kind"] == "quotation" and len(q.get("items",[])) > 0]
    print(f"\n[DATOS] Total cotizaciones: {len(quotes)} | Pendientes con items: {len(pending)}")
    return [q["id"] for q in pending]

def emit_async(token, cot_id, user_idx):
    """Emite factura async"""
    start = time.time()
    try:
        r = requests.post(
            f"{BASE}/cotizaciones/{cot_id}/facturar?mode=async",
            headers=get_headers(token),
            json={"tipo_comprobante": "03"},
            timeout=15,
        )
        elapsed = (time.time() - start) * 1000
        return {"user": user_idx, "status": r.status_code, "ms": elapsed, "ok": r.status_code in (200, 202)}
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return {"user": user_idx, "status": 0, "ms": elapsed, "ok": False, "error": str(e)[:100]}

def emit_sync(token, cot_id, user_idx):
    """Emite factura sync"""
    start = time.time()
    try:
        r = requests.post(
            f"{BASE}/cotizaciones/{cot_id}/facturar",
            headers=get_headers(token),
            json={"tipo_comprobante": "03"},
            timeout=60,
        )
        elapsed = (time.time() - start) * 1000
        return {"user": user_idx, "status": r.status_code, "ms": elapsed, "ok": r.status_code in (200, 202)}
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return {"user": user_idx, "status": 0, "ms": elapsed, "ok": False, "error": str(e)[:100]}

def run_test(num_users, mode="async"):
    print(f"\n{'='*70}")
    print(f"  PRUEBA DE CARGA: {num_users} usuarios | Modo: {mode}")
    print(f"{'='*70}")

    token = get_token()
    quote_ids = count_pending_quotes(token)

    if len(quote_ids) < num_users:
        print(f"\n  [WARN] Solo hay {len(quote_ids)} cotizaciones pendientes, necesitamos {num_users}")
        print(f"  [WARN] Reduciendo a {len(quote_ids)} usuarios...")
        num_users = len(quote_ids)

    if num_users == 0:
        print("  [ERROR] No hay cotizaciones para probar")
        sys.exit(1)

    results = []
    started_at = time.time()

    print(f"\n[TEST] Ejecutando {num_users} requests concurrentes...")

    # Simular concurrencia con threads
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = {}
        for i in range(num_users):
            cot_id = quote_ids[i]
            emit_fn = emit_async if mode == "async" else emit_sync
            future = executor.submit(emit_fn, token, cot_id, i)
            futures[future] = i

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if (len(results) % 10 == 0) or len(results) == num_users:
                ok_count = sum(1 for r in results if r["ok"])
                print(f"  [{len(results)}/{num_users}] Exitosos: {ok_count} | Fallidos: {len(results)-ok_count}")

    total_time = time.time() - started_at

    # Reporte
    successful = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]
    latencies = sorted([r["ms"] for r in results if r["ms"] > 0])

    print(f"\n{'─'*70}")
    print(f"  RESULTADOS — {num_users} usuarios, modo {mode}")
    print(f"{'─'*70}")
    print(f"  Tiempo total:     {total_time:.2f}s")
    print(f"  Exitosos:         {len(successful)}/{num_users} ({len(successful)/num_users*100:.0f}%)")
    print(f"  Fallidos:         {len(failed)}/{num_users}")

    # Status codes
    codes = {}
    for r in results:
        codes[r["status"]] = codes.get(r["status"], 0) + 1
    for code, count in sorted(codes.items()):
        print(f"    HTTP {code}: {count}")

    if latencies:
        p50 = latencies[len(latencies)//2]
        p90_idx = int(len(latencies) * 0.9)
        p99_idx = min(int(len(latencies) * 0.99), len(latencies)-1)
        print(f"\n  Latencia (ms):")
        print(f"    Min:    {latencies[0]:.0f}")
        print(f"    P50:    {p50:.0f}")
        print(f"    P90:    {latencies[p90_idx]:.0f}")
        print(f"    P99:    {latencies[p99_idx]:.0f}")
        print(f"    Max:    {latencies[-1]:.0f}")
        print(f"    Prom:   {sum(latencies)/len(latencies):.0f}")

    rps = num_users / total_time if total_time > 0 else 0
    print(f"\n  Throughput:       {rps:.1f} requests/segundo")

    if failed:
        print(f"\n  Errores:")
        for f_item in failed[:5]:
            print(f"    User {f_item['user']}: HTTP {f_item['status']} — {f_item.get('error','?')}")

    # Veredicto
    rate = len(successful) / num_users * 100 if num_users > 0 else 0
    if rate >= 95:
        verdict = "PASS"
    elif rate >= 80:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    print(f"\n{'='*70}")
    print(f"  VEREDICTO: {verdict} — {rate:.0f}% exitoso")
    print(f"{'='*70}")

    # Guardar
    os.makedirs("pruebas", exist_ok=True)
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "users": num_users,
        "total_time_s": round(total_time, 2),
        "success_rate_pct": round(rate, 1),
        "throughput_rps": round(rps, 2),
        "latency_ms": {
            "min": round(latencies[0], 0) if latencies else 0,
            "p50": round(p50, 0) if latencies else 0,
            "p90": round(latencies[p90_idx], 0) if latencies else 0,
            "p99": round(latencies[p99_idx], 0) if latencies else 0,
            "max": round(latencies[-1], 0) if latencies else 0,
        },
        "errors": [{"user": f["user"], "status": f["status"]} for f in failed],
    }
    filename = f"pruebas/load_test_{mode}_{num_users}users_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  Reporte: {filename}")

    return report

if __name__ == "__main__":
    # Test escalonado: 5, 10, 15, 20, 25 usuarios async
    for n in [5, 10, 15, 20, 25, 30]:
        run_test(n, mode="async")
        time.sleep(2)
