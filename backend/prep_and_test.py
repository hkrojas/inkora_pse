"""prep_and_test.py — Crea datos directamente en DB y corre prueba"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from datetime import datetime, timezone

# ── 1. Crear cotizaciones directo en DB (sin PDF background tasks) ──
print("[1/3] Creando cotizaciones de prueba directo en DB...")
from database import SessionLocal
import models
from security import get_password_hash

db = SessionLocal()

# Get tenant and user
tenant = db.query(models.Tenant).filter(models.Tenant.business_ruc == '20999999999').first()
if not tenant:
    tenant = db.query(models.Tenant).first()
user = db.query(models.User).filter(models.User.email == 'admin@demo.inkora.pe').first()
if not user:
    user = db.query(models.User).filter(models.User.tenant_id == tenant.id).first()
cliente = db.query(models.Cliente).filter(models.Cliente.tenant_id == tenant.id).first()

print(f"  Tenant: {tenant.business_name} (id={tenant.id})")
print(f"  User: {user.email} (id={user.id})")
print(f"  Cliente: {cliente.razon_social} (id={cliente.id})")

# Create 60 test quotes directly
for i in range(60):
    cot = models.Cotizacion(
        tenant_id=tenant.id,
        cliente_id=cliente.id,
        usuario_id=user.id,
        fecha_emision=datetime.now(timezone.utc),
        serie="COT",
        correlativo=9000+i,
        document_kind="quotation",
        tipo_comprobante="00",
        estado="pendiente",
        total_gravada=Decimal("100.00"),
        total_igv=Decimal("18.00"),
        total_venta=Decimal("118.00"),
        monto_pagado=Decimal("0.00"),
        saldo_pendiente=Decimal("118.00"),
        moneda="PEN",
    )
    db.add(cot)
    db.flush()

    item = models.CotizacionItem(
        cotizacion_id=cot.id,
        descripcion=f"Servicio test {i+1}",
        cantidad=1,
        precio_unitario=Decimal("118.00"),
        valor_unitario=Decimal("100.00"),
        total_base_igv=Decimal("100.00"),
        total_igv=Decimal("18.00"),
        total_item=Decimal("118.00"),
        unidad_medida="NIU",
        tipo_afectacion_igv="10",
    )
    db.add(item)

db.commit()
print(f"  [OK] 60 cotizaciones creadas")
db.close()

# ── 2. Login y obtener IDs ──
print("\n[2/3] Login y obteniendo IDs...")
BASE = "http://127.0.0.1:8000"
EMAIL = "admin@demo.inkora.pe"
PASSWORD = "demo1234"

r = requests.post(f"{BASE}/token", data={"username":EMAIL,"password":PASSWORD,"grant_type":"password"}, timeout=10)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

r2 = requests.get(f"{BASE}/cotizaciones/?limit=200", headers=headers, timeout=30)
quotes = r2.json()
ids = [q["id"] for q in quotes if q["estado"]=="pendiente" and q["document_kind"]=="quotation"]
print(f"  [OK] {len(ids)} cotizaciones pendientes listas")

# ── 3. Prueba de carga ──
def emit_async(t, cid, idx):
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/cotizaciones/{cid}/facturar?mode=async",
            headers={"Authorization": f"Bearer {t}"},
            json={"tipo_comprobante":"03"}, timeout=20)
        return {"ok": r.status_code in (200,202), "code": r.status_code, "ms": (time.time()-t0)*1000}
    except Exception as e:
        return {"ok": False, "code": 0, "ms": (time.time()-t0)*1000, "err": str(e)[:80]}

print(f"\n[3/3] Prueba de carga escalonada...")
print("="*70)

all_reports = []
for n in [5, 10, 15, 20, 25, 30]:
    if n > len(ids):
        break

    print(f"\n  >>> {n} usuarios async concurrentes...")
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
                print(f"    [{done}/{n}] Exitosos: {ok_c}")

    elapsed = time.time() - t0
    ok = sum(1 for r in results if r["ok"])
    lat = sorted(r["ms"] for r in results)
    codes = {}
    for r in results:
        codes[r["code"]] = codes.get(r["code"],0)+1

    p50 = lat[len(lat)//2] if lat else 0
    p90 = lat[int(len(lat)*0.9)] if lat else 0
    p99 = lat[min(int(len(lat)*0.99),len(lat)-1)] if lat else 0

    print(f"  Tiempo: {elapsed:.1f}s | Exitosos: {ok}/{n} ({ok/n*100:.0f}%) | RPS: {n/elapsed:.1f}")
    print(f"  Status: {codes}")
    if lat:
        print(f"  Latencia ms -> Min:{lat[0]:.0f} P50:{p50:.0f} P90:{p90:.0f} P99:{p99:.0f} Max:{lat[-1]:.0f} Prom:{sum(lat)/len(lat):.0f}")

    verdict = "PASS" if ok/n>=0.95 else "WARN" if ok/n>=0.80 else "FAIL"
    print(f"  VEREDICTO: {verdict}")

    all_reports.append({
        "users":n, "ok_pct":round(ok/n*100,1),
        "p50":round(p50,0), "p90":round(p90,0), "p99":round(p99,0),
        "rps":round(n/elapsed,2), "verdict":verdict, "codes":codes
    })

    time.sleep(3)

# Summary table
print("\n" + "="*70)
print("  RESUMEN — Facturación Async Local")
print("="*70)
print(f"  {'Users':<8} {'Tasa%':<8} {'P50ms':<8} {'P90ms':<8} {'P99ms':<8} {'RPS':<8} {'Veredicto'}")
print(f"  {'─'*65}")
for rp in all_reports:
    print(f"  {rp['users']:<8} {rp['ok_pct']:<8} {rp['p50']:<8} {rp['p90']:<8} {rp['p99']:<8} {rp['rps']:<8} {rp['verdict']}")
print("="*70)

# Save
os.makedirs("pruebas", exist_ok=True)
fn = f"pruebas/load_test_final_{time.strftime('%Y%m%d_%H%M%S')}.json"
with open(fn,"w",encoding="utf-8") as f:
    json.dump({"timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),"results":all_reports},f,indent=2)
print(f"\n  Reporte: {fn}")
