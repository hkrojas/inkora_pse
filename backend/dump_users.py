"""dump_users.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models

db = SessionLocal()
users = db.query(models.User).all()
lines = ['=== USUARIOS DISPONIBLES ===', '']

# Known passwords from seed scripts and test setup
KNOWN_PASSWORDS = {
    "admin@demo.inkora.pe": "demo1234",
    "backend.apisperu.verify.20260411_140659@printflow.pe": "test123456",
    "admin@printflow.com": "admin123",
}

for u in users:
    t = db.query(models.Tenant).filter(models.Tenant.id == u.tenant_id).first()
    tenant_name = t.business_name if t else 'N/A'
    super_label = 'SUPERADMIN' if u.is_superadmin else u.rol.upper()
    password = KNOWN_PASSWORDS.get(u.email, '(contraseña desconocida — revisar seed script)')
    lines.append(f'  Email:       {u.email}')
    lines.append(f'  Password:    {password}')
    lines.append(f'  Tenant:      {tenant_name} (id={u.tenant_id})')
    lines.append(f'  Rol:         {super_label}')
    lines.append(f'  Activo:      {t.is_active if t else "N/A"}')
    lines.append('')

db.close()

with open("_users_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("OK — archivo _users_output.txt creado")
