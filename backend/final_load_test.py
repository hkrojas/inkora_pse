"""final_load_test.py — Flujo correcto con tenant 7 (ApisPeru real)"""
import requests, time, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "http://127.0.0.1:8000"
EMAIL_T7 = "backend.apisperu.verify.20260411_140659@printflow.pe"
PASS_T7 = "test123456"

def main():
    print("="*70)
    print("  PRUEBA FINAL — Tenant 7: PAPELERIA GRAFICA (ApisPeru REAL)")
    print("  Flujo: login tenant7 -> validar token -> crear cliente")
    print("         -> crear cotizaciones -> facturar concurrente")
    print("="*70)

    # ── 1. Login tenant 7 ──
    print("\n[1/5] Login usuario tenant 7...")
    r = requests.post(f"{BASE}/token", data={
        "username":EMAIL_T7,"password":PASS_T7,"grant_type":"password"
    }, timeout=10)
    if r.status_code != 200:
        print(f"  FAIL: {r.status_code} {r.text[:200]}"); sys.exit(1)
    t = r.json()["access_token"]
    hdr = {"Authorization": f"Bearer {t}"}

    r2 = requests.get(f"{BASE}/users/me/", headers=hdr, timeout=10)
    user = r2.json()
    print(f"  User: {user['email']} | Tenant: {user['tenant_id']} | Rol: {user['rol']}")

    # ── 2. Validar token ApisPeru ──
    print("\n[2/5] Validando token ApisPeru del tenant...")
    r3 = requests.get(f"{BASE}/consultar-documento/20191308868", headers=hdr, timeout=15)
    print(f"  Consulta RUC: {r3.status_code}")
    if r3.status_code == 200:
        print(f"  RUC: {r3.json().get('razon_social','?')}")

    # ── 3. Crear cliente ──
    print("\n[3/5] Creando cliente de prueba...")
    cliente_payload = {
        "tipo_documento": "6",
        "numero_documento": "20191308868",
        "razon_social": "ARCOR DE PERU SA",
        "direccion": "Av. Industrial 123 Lima",
    }
    r4 = requests.post(f"{BASE}/clientes/", headers=hdr, json=cliente_payload, timeout=10)
    if r4.status_code in (200, 201):
        cliente_id = r4.json()["id"]
        print(f"  Cliente creado id={cliente_id}")
    elif r4.status_code == 409:
        r4b = requests.get(f"{BASE}/clientes/?q=20191308868&limit=1", headers=hdr, timeout=10)
        cliente_id = r4b.json()[0]["id"]
        print(f"  Cliente existente id={cliente_id}")
    else:
        print(f"  FAIL: {r4.status_code} {r4.text[:200]}"); sys.exit(1)

    # ── 4. Crear 30 cotizaciones ──
    print(f"\n[4/5] Creando 30 cotizaciones...")
    ids = []
    for i in range(30):
        r5 = requests.post(f"{BASE}/cotizaciones/", headers=hdr, json={
            "cliente_id": cliente_id,
            "moneda": "PEN",
            "tipo_comprobante": "00",
            "items": [{"descripcion":f"Servicio-{i+1}-{os.urandom(4).hex()}","cantidad":1,"precio_unitario":118.00}]
        }, timeout=15)
        if r5.status_code in (200, 201):
            ids.append(r5.json()["id"])
            if (i+1) % 10 == 0:
                print(f"    {i+1}/30 creadas...")
        else:
            print(f"    FAIL {i}: {r5.status_code}")
    print(f"  [OK] {len(ids)} cotizaciones")

    if len(ids) < 3:
        print("  [FAIL] Sin cotizaciones"); sys.exit(1)

    # ── 5. Prueba de carga async ──
    def emit_async(cid, idx):
        t0 = time.time()
        try:
            r = requests.post(f"{BASE}/cotizaciones/{cid}/facturar?mode=async",
                headers=hdr, json={"tipo_comprobante":"03"}, timeout=20)
            return {"ok":r.status_code in(200,202),"code":r.status_code,
                    "ms":(time.time()-t0)*1000, "body":r.text[:150]}
        except Exception as e:
            return {"ok":False,"code":0,"ms":(time.time()-t0)*1000,"err":str(e)[:80]}

    print(f"\n[5/5] Prueba de carga concurrente...")
    all_reports = []
    for n in [3, 5, 10, 15, 20, 25]:
        if n > len(ids): break
        print(f"\n  >>> {n} usuarios concurrentes (async)...")
        results = []
        t0 = time.time()

        with ThreadPoolExecutor(max_workers=n) as ex:
            futs = {ex.submit(emit_async, ids[i], i): i for i in range(n)}
            for f in as_completed(futs):
                results.append(f.result())

        elapsed = time.time() - t0
        ok = sum(1 for r in results if r["ok"])
        lat = sorted(r["ms"] for r in results if r["ms"] > 0)
        codes = {}
        for r in results: codes[r["code"]] = codes.get(r["code"],0)+1

        p50 = lat[len(lat)//2] if lat else 0
        p90 = lat[int(len(lat)*0.9)] if lat else 0
        p99 = lat[min(int(len(lat)*0.99),len(lat)-1)] if lat else 0

        print(f"  Tiempo: {elapsed:.1f}s | Exitosos: {ok}/{n} ({ok/n*100:.0f}%)")
        print(f"  Status codes: {codes}")
        if lat:
            print(f"  Latencia ms -> Min:{lat[0]:.0f} P50:{p50:.0f} P90:{p90:.0f} P99:{p99:.0f} Max:{lat[-1]:.0f}")

        fails = [r for r in results if not r["ok"]]
        if fails:
            print(f"  Errores ({len(fails)}):")
            for fe in fails[:3]:
                print(f"    HTTP {fe['code']}: {fe.get('body','?')[:120]}")

        verdict = "PASS" if ok/n>=0.95 else "WARN" if ok/n>=0.80 else "FAIL"
        print(f"  VEREDICTO: {verdict}")

        all_reports.append({
            "users":n, "ok_pct":round(ok/n*100,1),
            "p50":round(p50,0) if lat else 0,
            "p90":round(p90,0) if lat else 0,
            "p99":round(p99,0) if lat else 0,
            "max_ms":round(lat[-1],0) if lat else 0,
            "verdict":verdict, "codes":codes
        })
        time.sleep(5)

    # Resumen final
    print("\n" + "="*70)
    print("  RESUMEN — Tenant 7 PAPELERIA GRAFICA (ApisPeru REAL)")
    print("="*70)
    print(f"  {'Users':<8} {'Tasa%':<8} {'P50ms':<8} {'P90ms':<8} {'P99ms':<8} {'Max':<8} {'Veredicto'}")
    print(f"  {'─'*65}")
    for rp in all_reports:
        print(f"  {rp['users']:<8} {rp['ok_pct']:<8} {rp['p50']:<8} {rp['p90']:<8} {rp['p99']:<8} {rp['max_ms']:<8} {rp['verdict']}")
    print("="*70)

    # Guardar
    os.makedirs("pruebas", exist_ok=True)
    fn = f"pruebas/load_test_FINAL_tenant7_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(fn,"w",encoding="utf-8") as f:
        json.dump({"tenant":7,"tenant_name":"PAPELERIA GRAFICA Y PUBLICITARIA SAC",
                    "timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),"results":all_reports},f,indent=2)
    print(f"\n  Reporte: {fn}")

if __name__ == "__main__":
    main()
