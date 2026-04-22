"""simple_load_test.py — Prueba de carga mínima sin relaciones pesadas"""
import requests, time, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "http://127.0.0.1:8000"
EMAIL = "admin@demo.inkora.pe"
PASSWORD = "demo1234"

def get_token():
    r = requests.post(f"{BASE}/token", data={"username":EMAIL,"password":PASSWORD,"grant_type":"password"}, timeout=10)
    if r.status_code != 200:
        print(f"Login FAIL: {r.status_code}"); sys.exit(1)
    return r.json()["access_token"]

def hdr(t): return {"Authorization": f"Bearer {t}"}

# ── Crear cotizaciones SIN items via API (no dispara PDF con items) ──
def create_simple_quote(token):
    """Crea cotización con un item mínimo"""
    r = requests.post(f"{BASE}/cotizaciones/", headers=hdr(token), json={
        "cliente_id": 3,
        "moneda": "PEN",
        "tipo_comprobante": "00",
        "items": [{"descripcion":"Test","cantidad":1,"precio_unitario":118.00}]
    }, timeout=10)
    if r.status_code in (200, 201):
        return r.json()["id"]
    print(f"  Create FAIL: {r.status_code} {r.text[:100]}")
    return None

# ── Emitir async ──
def emit_async(token, cid, idx):
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/cotizaciones/{cid}/facturar?mode=async",
            headers=hdr(token), json={"tipo_comprobante":"03"}, timeout=15)
        return {"ok": r.status_code in (200,202), "code": r.status_code, "ms": (time.time()-t0)*1000}
    except Exception as e:
        return {"ok": False, "code": 0, "ms": (time.time()-t0)*1000, "err": str(e)[:80]}

def main():
    print("="*70)
    print(f"  PRUEBA DE CARGA LOCAL — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    token = get_token()
    print("[OK] Login")

    # Crear 50 cotizaciones
    print("\nCreando 50 cotizaciones de prueba...")
    ids = []
    for i in range(50):
        cid = create_simple_quote(token)
        if cid:
            ids.append(cid)
            if (i+1) % 10 == 0:
                print(f"  {i+1}/50 creadas...")
    print(f"[OK] {len(ids)} cotizaciones listas")

    if len(ids) < 5:
        print("[FAIL] No se pudieron crear cotizaciones")
        sys.exit(1)

    # Test escalonado
    all_reports = []
    for n in [5, 10, 15, 20, 25, 30, 40, 50]:
        if n > len(ids):
            break
        print(f"\n>>> {n} usuarios async concurrentes...")
        results = []
        t0 = time.time()

        with ThreadPoolExecutor(max_workers=n) as ex:
            futs = {ex.submit(emit_async, token, ids[i], i): i for i in range(n)}
            done = 0
            for f in as_completed(futs):
                results.append(f.result())
                done += 1
                if done % 5 == 0:
                    ok_c = sum(1 for r in results if r["ok"])
                    print(f"  [{done}/{n}] OK: {ok_c}")

        elapsed = time.time() - t0
        ok = sum(1 for r in results if r["ok"])
        lat = sorted(r["ms"] for r in results)
        codes = {}
        for r in results: codes[r["code"]] = codes.get(r["code"],0)+1

        p50 = lat[len(lat)//2] if lat else 0
        p90 = lat[int(len(lat)*0.9)] if lat else 0
        p99 = lat[min(int(len(lat)*0.99),len(lat)-1)] if lat else 0

        print(f"  Tiempo: {elapsed:.1f}s | Exitosos: {ok}/{n} ({ok/n*100:.0f}%) | RPS: {n/elapsed:.1f}")
        print(f"  Status: {codes}")
        if lat:
            print(f"  Latencia ms -> Min:{lat[0]:.0f} P50:{p50:.0f} P90:{p90:.0f} P99:{p99:.0f} Max:{lat[-1]:.0f} Prom:{sum(lat)/len(lat):.0f}")

        verdict = "PASS" if ok/n>=0.95 else "WARN" if ok/n>=0.80 else "FAIL"
        print(f"  VEREDICTO: {verdict}")

        all_reports.append({"users":n,"ok_pct":round(ok/n*100,1),"p50":round(p50,0),"p90":round(p90,0),"p99":round(p99,0),"rps":round(n/elapsed,2),"verdict":verdict,"codes":codes})
        time.sleep(3)

    # Summary
    print("\n" + "="*70)
    print("  RESUMEN — Facturación Async Local")
    print("="*70)
    print(f"  {'Users':<8} {'Tasa%':<8} {'P50ms':<8} {'P90ms':<8} {'P99ms':<8} {'RPS':<8} {'Veredicto'}")
    print(f"  {'─'*65}")
    for rp in all_reports:
        print(f"  {rp['users']:<8} {rp['ok_pct']:<8} {rp['p50']:<8} {rp['p90']:<8} {rp['p99']:<8} {rp['rps']:<8} {rp['verdict']}")
    print("="*70)

    os.makedirs("pruebas", exist_ok=True)
    fn = f"pruebas/load_test_final_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(fn,"w",encoding="utf-8") as f:
        json.dump({"timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),"results":all_reports},f,indent=2)
    print(f"\n  Reporte: {fn}")

if __name__ == "__main__":
    main()
