"""
setup_load_test.py — Prepara datos de prueba para test_concurrent_billing.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import json

BASE = "http://127.0.0.1:8000"

def main():
    # Login
    print("[1/3] Login...")
    r = requests.post(f"{BASE}/token", data={
        "username": "admin@demo.inkora.pe",
        "password": "demo1234",
        "grant_type": "password",
    }, timeout=10)
    if r.status_code != 200:
        print(f"  FAIL: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    token = r.json()["access_token"]
    print(f"  OK token={token[:30]}...")
    headers = {"Authorization": f"Bearer {token}"}

    # Get client
    print("[2/3] Finding client...")
    r = requests.get(f"{BASE}/clientes/?limit=1", headers=headers, timeout=10)
    if r.status_code != 200 or not r.json():
        print("  FAIL: No clients found")
        sys.exit(1)
    cliente = r.json()[0]
    print(f"  OK client={cliente['razon_social']} id={cliente['id']}")

    # Create 50 test quotes
    print("[3/3] Creating 50 test quotes...")
    for i in range(50):
        payload = {
            "cliente_id": cliente["id"],
            "moneda": "PEN",
            "tipo_comprobante": "00",
            "items": [
                {
                    "descripcion": f"Test quote item {i+1} - {os.urandom(4).hex()}",
                    "cantidad": 1,
                    "precio_unitario": 118.00,
                }
            ],
        }
        r = requests.post(f"{BASE}/cotizaciones/", headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=15)
        if r.status_code in (200, 201):
            print(f"  {i+1}/50 created id={r.json()['id']}")
        else:
            print(f"  {i+1}/50 FAILED {r.status_code} {r.text[:100]}")

    # List all pending quotes
    print("\nPending quotes:")
    r = requests.get(f"{BASE}/cotizaciones/?limit=100", headers=headers, timeout=10)
    quotes = r.json()
    pending = [q for q in quotes if q["estado"] == "pendiente" and q["document_kind"] == "quotation"]
    print(f"  Total: {len(quotes)} | Pending with items: {len(pending)}")
    for q in pending[:5]:
        print(f"    id={q['id']} estado={q['estado']} items={len(q.get('items',[]))}")

    # Save config for test script
    config = {
        "base_url": BASE,
        "email": "admin@demo.inkora.pe",
        "password": "demo1234",
    }
    with open("load_test_config.json", "w") as f:
        json.dump(config, f)
    print(f"\nConfig saved to load_test_config.json")

if __name__ == "__main__":
    main()
