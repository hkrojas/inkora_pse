"""check_tenant7.py — Verificar usuarios y config del tenant 7"""
import sys; sys.path.insert(0,'.')
from database import SessionLocal
import models

db = SessionLocal()

# Tenant 7
t7 = db.query(models.Tenant).filter(models.Tenant.id==7).first()
if t7:
    print(f"Tenant 7: {t7.business_name}")
    print(f"  RUC: {t7.business_ruc}")
    print(f"  is_active: {t7.is_active}")
    print(f"  apisperu_token: {'YES' if t7.apisperu_token else 'NO'}")
    print(f"  apisperu_url: {t7.apisperu_url or 'default'}")
else:
    print("Tenant 7 NO EXISTE")

# Usuarios del tenant 7
users7 = db.query(models.User).filter(models.User.tenant_id==7).all()
print(f"\nUsuarios en tenant 7: {len(users7)}")
for u in users7:
    print(f"  {u.email} | rol={u.rol} | super={u.is_superadmin}")

# Tenant 6
t6 = db.query(models.Tenant).filter(models.Tenant.id==6).first()
if t6:
    print(f"\nTenant 6: {t6.business_name}")
    print(f"  apisperu_token: {'YES' if t6.apisperu_token else 'NO'}")
    print(f"  token value: {t6.apisperu_token[:20] if t6.apisperu_token else 'NONE'}")

db.close()
