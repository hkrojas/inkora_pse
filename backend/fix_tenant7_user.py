"""fix_tenant7_user.py — Resetear password de un usuario del tenant 7"""
import sys; sys.path.insert(0,'.')
from database import SessionLocal
import models
from security import get_password_hash

db = SessionLocal()

# Reset password del primer usuario del tenant 7
u = db.query(models.User).filter(models.User.tenant_id==7).first()
if u:
    u.hashed_password = get_password_hash("test123456")
    db.commit()
    print(f"Password reseteada para: {u.email}")
    print(f"Nuevo password: test123456")
    print(f"Tenant: {u.tenant_id}")
else:
    print("No hay usuarios en tenant 7")

db.close()
