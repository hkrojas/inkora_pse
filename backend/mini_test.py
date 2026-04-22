"""mini_test.py — Prueba mínima de 3 usuarios"""
import requests, time, json

BASE = "http://127.0.0.1:8000"
EMAIL, PASSWORD = "admin@demo.inkora.pe", "demo1234"

r = requests.post(f"{BASE}/token", data={"username":EMAIL,"password":PASSWORD,"grant_type":"password"}, timeout=10)
t = r.json()["access_token"]
h = {"Authorization": f"Bearer {t}"}

# Verificar tenant
r2 = requests.get(f"{BASE}/users/me/", headers=h, timeout=10)
user = r2.json()
print(f"User: {user['email']} tenant_id={user.get('tenant_id')}")

# Crear 5 cotizaciones
ids = []
for i in range(5):
    r3 = requests.post(f"{BASE}/cotizaciones/", headers=h, json={
        "cliente_id": 3, "moneda":"PEN", "tipo_comprobante":"00",
        "items": [{"descripcion":f"Mini-{i}","cantidad":1,"precio_unitario":118.00}]
    }, timeout=10)
    if r3.status_code in (200,201):
        ids.append(r3.json()["id"])
        print(f"  Created quote {ids[-1]}")
    else:
        print(f"  Create FAIL: {r3.status_code} {r3.text[:100]}")

# Probar emisión de una
if ids:
    print(f"\nProbando emisión de quote {ids[0]}...")
    r4 = requests.post(f"{BASE}/cotizaciones/{ids[0]}/facturar?mode=async", headers=h, json={"tipo_comprobante":"03"}, timeout=15)
    print(f"  Status: {r4.status_code}")
    print(f"  Body: {r4.text[:500]}")
