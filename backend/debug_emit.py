"""debug_emit.py"""
import requests
r = requests.post('http://127.0.0.1:8000/token', data={'username':'admin@demo.inkora.pe','password':'demo1234','grant_type':'password'}, timeout=10)
t = r.json()['access_token']

# Check tenant
r2 = requests.get('http://127.0.0.1:8000/users/me/', headers={'Authorization':f'Bearer {t}'}, timeout=10)
user_data = r2.json()
with open('_debug_output.txt','w') as f:
    f.write(f"User: {r2.status_code}\n")
    f.write(f"Tenant ID: {user_data.get('tenant_id')}\n")

# Try one emission
r3 = requests.post('http://127.0.0.1:8000/cotizaciones/516/facturar?mode=async', headers={'Authorization':f'Bearer {t}'}, json={'tipo_comprobante':'03'}, timeout=15)
with open('_debug_output.txt','a') as f:
    f.write(f"\nEmit 516: {r3.status_code}\n")
    f.write(f"Body: {r3.text[:500]}\n")

# Check tenant config via superadmin endpoint
r4 = requests.get('http://127.0.0.1:8000/tenants/', headers={'Authorization':f'Bearer {t}'}, timeout=10)
with open('_debug_output.txt','a') as f:
    f.write(f"\nTenants list: {r4.status_code}\n")
    if r4.status_code == 200:
        tenants = r4.json()
        for tn in tenants:
            if tn['id'] == user_data.get('tenant_id'):
                f.write(f"  Tenant {tn['id']}: active={tn.get('is_active')} apisperu={tn.get('apisperu_token','')[:10] if tn.get('apisperu_token') else 'NONE'}\n")
