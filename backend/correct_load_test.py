"""correct_load_test.py — Sigue el flujo documentado en APISPERU_FLUJO_EMISION.md seccion 12"""
import requests, time, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "http://127.0.0.1:8000"

def main():
    print("="*70)
    print("  PRUEBA CON FLUJO CORRECTO — Tenant 7 (ApisPeru real)")
    print("  Flujo: superadmin -> crear usuario -> login -> validar token")
    print("         -> crear cliente -> cotizar -> facturar")
    print("="*70)

    # ── Paso 1: Login superadmin ──
    print("\n[1/6] Login superadmin...")
    r = requests.post(f"{BASE}/token", data={
        "username":"admin@demo.inkora.pe","password":"demo1234","grant_type":"password"
    }, timeout=10)
    if r.status_code != 200:
        print(f"  FAIL: {r.status_code} {r.text[:200]}"); sys.exit(1)
    admin_token = r.json()["access_token"]
    admin_hdr = {"Authorization": f"Bearer {admin_token}"}
    print(f"  OK token={admin_token[:30]}...")

    # ── Paso 2: Crear usuario en tenant 7 ──
    print("\n[2/6] Creando usuario en tenant 7 (PAPELERIA GRAFICA)...")
    test_email = f"lt_{int(time.time())}@pf.com"
    r2 = requests.post(f"{BASE}/superadmin/tenants/7/users", headers=admin_hdr, json={
        "email": test_email,
        "password": "lt123456",
        "nombre_completo": "Load Test",
        "rol": "admin"
    }, timeout=10)
    if r2.status_code not in (200, 201):
        print(f"  WARN crear usuario: {r2.status_code} — usando superadmin directo")
        test_email = "admin@demo.inkora.pe"
        t_token = admin_token
        t_hdr = admin_hdr
    else:
        print(f"  Usuario creado: {test_email}")
        # ── Paso 3: Login con usuario del tenant 7 ──
        print("\n[3/6] Login usuario tenant 7...")
        r3 = requests.post(f"{BASE}/token", data={
            "username":test_email,"password":"lt123456","grant_type":"password"
        }, timeout=10)
        if r3.status_code != 200:
            print(f"  FAIL login tenant 7: {r3.status_code} {r3.text[:200]}"); sys.exit(1)
        t_token = r3.json()["access_token"]
        t_hdr = {"Authorization": f"Bearer {t_token}"}
        print(f"  OK")

    # Verificar tenant
    r4 = requests.get(f"{BASE}/users/me/", headers=t_hdr, timeout=10)
    user = r4.json()
    print(f"  Tenant ID: {user.get('tenant_id')} | Rol: {user.get('rol')}")

    # ── Paso 4: Validar token ApisPeru ──
    print("\n[4/6] Validando token ApisPeru del tenant...")
    r5 = requests.post(f"{BASE}/superadmin/validate/apisperu-token", headers=t_hdr, timeout=15)
    print(f"  Status: {r5.status_code}")
    if r5.status_code == 200:
        v = r5.json()
        print(f"  Result: {v}")
    else:
        print(f"  Body: {r5.text[:300]}")

    # ── Paso 5: Crear cliente via consulta documental + CRUD ──
    print("\n[5/6] Creando cliente de prueba...")
    # Consultar RUC primero
    r6 = requests.get(f"{BASE}/consultar-documento/20191308868", headers=t_hdr, timeout=15)
    if r6.status_code == 200:
        doc_data = r6.json()
        print(f"  RUC consultado: {doc_data.get('razon_social','?')}")
    else:
        print(f"  Consulta RUC: {r6.status_code}")
        doc_data = {}

    # Crear cliente
    cliente_payload = {
        "tipo_documento": "6",
        "numero_documento": "20191308868",
        "razon_social": doc_data.get("razon_social", "ARCOR DE PERU SA"),
        "direccion": doc_data.get("direccion", "Av. Test 123"),
    }
    r7 = requests.post(f"{BASE}/clientes/", headers=t_hdr, json=cliente_payload, timeout=10)
    if r7.status_code in (200, 201, 409):
        # 409 = ya existe, buscarlo
        if r7.status_code == 409:
            r7b = requests.get(f"{BASE}/clientes/?q=20191308868&limit=1", headers=t_hdr, timeout=10)
            if r7b.status_code == 200 and r7b.json():
                cliente_id = r7b.json()[0]["id"]
                print(f"  Cliente existente id={cliente_id}")
            else:
                print(f"  FAIL encontrar cliente existente"); sys.exit(1)
        else:
            cliente_id = r7.json()["id"]
            print(f"  Cliente creado id={cliente_id}")
    else:
        print(f"  FAIL crear cliente: {r7.status_code} {r7.text[:200]}"); sys.exit(1)

    # ── Paso 6: Crear cotizaciones y probar emisión ──
    print(f"\n[6/6] Creando 30 cotizaciones y probando emisión concurrente...")
    ids = []
    for i in range(30):
        r8 = requests.post(f"{BASE}/cotizaciones/", headers=t_hdr, json={
            "cliente_id": cliente_id,
            "moneda": "PEN",
            "tipo_comprobante": "00",
            "items": [{"descripcion":f"Servicio LT-{i+1}","cantidad":1,"precio_unitario":118.00}]
        }, timeout=15)
        if r8.status_code in (200, 201):
            ids.append(r8.json()["id"])
            if (i+1) % 10 == 0:
                print(f"    {i+1}/30 creadas...")
        else:
            print(f"    FAIL crear quote {i}: {r8.status_code} {r8.text[:100]}")

    print(f"  [OK] {len(ids)} cotizaciones listas")

    if len(ids) < 3:
        print("  [FAIL] No hay suficientes cotizaciones"); sys.exit(1)

    # Función de emisión async
    def emit_async(cid, idx):
        t0 = time.time()
        try:
            r = requests.post(f"{BASE}/cotizaciones/{cid}/facturar?mode=async",
                headers=t_hdr, json={"tipo_comprobante":"03"}, timeout=20)
            return {"ok":r.status_code in(200,202),"code":r.status_code,
                    "ms":(time.time()-t0)*1000, "body":r.text[:200]}
        except Exception as e:
            return {"ok":False,"code":0,"ms":(time.time()-t0)*1000,"err":str(e)[:80]}

    # Prueba escalonada
    all_reports = []
    for n in [3, 5, 10, 15, 20, 25]:
        if n > len(ids): break
        print(f"\n  >>> {n} usuarios concurrentes...")
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

        # Mostrar errores
        fails = [r for r in results if not r["ok"]]
        if fails:
            print(f"  Errores ({len(fails)}):")
            for fe in fails[:3]:
                print(f"    User {fe.get('body','?')[:100]}")

        verdict = "PASS" if ok/n>=0.95 else "WARN" if ok/n>=0.80 else "FAIL"
        print(f"  VEREDICTO: {verdict}")

        all_reports.append({
            "users":n, "ok_pct":round(ok/n*100,1),
            "p50":round(p50,0) if lat else 0,
            "p90":round(p90,0) if lat else 0,
            "p99":round(p99,0) if lat else 0,
            "verdict":verdict, "codes":codes
        })
        time.sleep(5)

    # Resumen
    print("\n" + "="*70)
    print("  RESUMEN FINAL — Facturación Async con Tenant 7 (ApisPeru real)")
    print("="*70)
    print(f"  {'Users':<8} {'Tasa%':<8} {'P50ms':<8} {'P90ms':<8} {'P99ms':<8} {'Veredicto'}")
    print(f"  {'─'*55}")
    for rp in all_reports:
        print(f"  {rp['users']:<8} {rp['ok_pct']:<8} {rp['p50']:<8} {rp['p90']:<8} {rp['p99']:<8} {rp['verdict']}")
    print("="*70)

    # Guardar
    os.makedirs("pruebas", exist_ok=True)
    fn = f"pruebas/load_test_correcto_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(fn,"w",encoding="utf-8") as f:
        json.dump({"tenant":7,"timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),"results":all_reports},f,indent=2)
    print(f"\n  Reporte: {fn}")

if __name__ == "__main__":
    main()
