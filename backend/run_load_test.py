"""run_load_test.py — Prueba de carga escalonada contra backend local"""
import requests, json, time, sys, os
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "http://127.0.0.1:8000"
EMAIL = "admin@demo.inkora.pe"
PASSWORD = "demo1234"

def token():
    r = requests.post(f"{BASE}/token", data={"username":EMAIL,"password":PASSWORD,"grant_type":"password"}, timeout=10)
    if r.status_code != 200:
        print(f"Login FAIL: {r.status_code} {r.text[:200]}"); sys.exit(1)
    return r.json()["access_token"]

def hdr(t):
    return {"Authorization": f"Bearer {t}"}

def get_pending_ids(t):
    r = requests.get(f"{BASE}/cotizaciones/?limit=200", headers=hdr(t), timeout=30)
    quotes = r.json()
    pending = [q["id"] for q in quotes if q["estado"]=="pendiente" and q["document_kind"]=="quotation" and len(q.get("items",[]))>0]
    return pending

def emit_async(t, cid, idx):
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/cotizaciones/{cid}/facturar?mode=async", headers=hdr(t), json={"tipo_comprobante":"03"}, timeout=20)
        return {"ok": r.status_code in (200,202), "code": r.status_code, "ms": (time.time()-t0)*1000}
    except Exception as e:
        return {"ok": False, "code": 0, "ms": (time.time()-t0)*1000, "err": str(e)[:80]}

def test(n, t, ids):
    print(f"\n  >>> {n} usuarios async concurrentes...")
    results = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=n) as ex:
        futs = {ex.submit(emit_async, t, ids[i], i): i for i in range(n)}
        for f in as_completed(futs):
            results.append(f.result())
    elapsed = time.time() - t0
    ok = sum(1 for r in results if r["ok"])
    lat = sorted(r["ms"] for r in results)
    codes = {}
    for r in results:
        codes[r["code"]] = codes.get(r["code"],0)+1

    p50 = lat[len(lat)//2] if lat else 0
    p90 = lat[int(len(lat)*0.9)] if lat else 0
    p99 = lat[min(int(len(lat)*0.99),len(lat)-1)] if lat else 0

    print(f"  Tiempo: {elapsed:.1f}s | Exitosos: {ok}/{n} ({ok/n*100:.0f}%) | Throughput: {n/elapsed:.1f} req/s")
    print(f"  Status codes: {codes}")
    print(f"  Latencia ms -> Min:{lat[0]:.0f} P50:{p50:.0f} P90:{p90:.0f} P99:{p99:.0f} Max:{lat[-1]:.0f} Prom:{sum(lat)/len(lat):.0f}" if lat else "  Sin latencia")

    verdict = "PASS" if ok/n>=0.95 else "WARN" if ok/n>=0.8 else "FAIL"
    print(f"  VEREDICTO: {verdict}")

    # Save report
    report = {
        "users": n, "mode": "async", "time_s": round(elapsed,2),
        "success_pct": round(ok/n*100,1), "rps": round(n/elapsed,2),
        "latency_ms": {"min":round(lat[0],0),"p50":round(p50,0),"p90":round(p90,0),"p99":round(p99,0),"max":round(lat[-1],0)} if lat else {},
        "status_codes": codes,
        "verdict": verdict,
    }
    os.makedirs("pruebas", exist_ok=True)
    fn = f"pruebas/load_local_async_{n}users_{time.strftime('%H%M%S')}.json"
    with open(fn,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print(f"  -> {fn}")
    return report

def main():
    print("="*70)
    print("  PRUEBA DE CARGA LOCAL — Facturación Async Simultánea")
    print(f"  Backend: {BASE} | Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    t = token()
    print("\n[OK] Login exitoso")

    ids = get_pending_ids(t)
    print(f"[OK] Cotizaciones pendientes: {len(ids)}")

    if len(ids) < 5:
        # Create some test quotes
        print("\n[CREANDO] Generando cotizaciones de prueba...")
        r = requests.get(f"{BASE}/clientes/?limit=1", headers=hdr(t), timeout=10)
        cliente_id = r.json()[0]["id"]
        for i in range(60):
            r2 = requests.post(f"{BASE}/cotizaciones/", headers=hdr(t), json={
                "cliente_id": cliente_id, "moneda":"PEN", "tipo_comprobante":"00",
                "items": [{"descripcion":f"Test-{i}-{os.urandom(4).hex()}","cantidad":1,"precio_unitario":118.00}]
            }, timeout=15)
            if r2.status_code in (200,201):
                ids.append(r2.json()["id"])
        print(f"[OK] Total cotizaciones: {len(ids)}")

    max_n = min(len(ids), 50)
    # Test escalonado
    sizes = [5, 10, 15, 20, 25, 30, 40, 50]
    sizes = [s for s in sizes if s <= max_n]

    all_reports = []
    for n in sizes:
        r = test(n, t, ids)
        all_reports.append(r)
        time.sleep(3)

    # Summary
    print("\n" + "="*70)
    print("  RESUMEN COMPARATIVO")
    print("="*70)
    print(f"  {'Usuarios':<10} {'Tasa':<10} {'P50ms':<10} {'P90ms':<10} {'P99ms':<10} {'RPS':<10} {'Veredicto'}")
    print(f"  {'─'*70}")
    for rp in all_reports:
        lat = rp.get("latency_ms",{})
        print(f"  {rp['users']:<10} {rp['success_pct']:<10} {lat.get('p50','?'):<10} {lat.get('p90','?'):<10} {lat.get('p99','?'):<10} {rp['rps']:<10} {rp['verdict']}")
    print("="*70)

if __name__ == "__main__":
    main()
