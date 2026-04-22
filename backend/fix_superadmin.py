"""fix_superadmin.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from security import get_password_hash

db = SessionLocal()

# Find the first tenant
t = db.query(models.Tenant).order_by(models.Tenant.id).first()
if not t:
    t = models.Tenant(business_name='PrintFlow', business_ruc='00000000000', is_active=True)
    db.add(t)
    db.commit()
    db.refresh(t)

# Check if superadmin exists
user = db.query(models.User).filter(models.User.email == 'admin@printflow.pe').first()
with open('_superadmin_fix.txt', 'w') as f:
    if user:
        f.write(f'EXISTE: {user.email}, tenant={user.tenant_id}, super={user.is_superadmin}\n')
        user.hashed_password = get_password_hash('superadmin123')
        user.is_superadmin = True
        user.rol = 'superadmin'
        db.commit()
        f.write('Password reseteada OK\n')
    else:
        new_user = models.User(
            email='admin@printflow.pe',
            hashed_password=get_password_hash('superadmin123'),
            nombre_completo='Superadmin PrintFlow',
            rol='superadmin',
            is_superadmin=True,
            tenant_id=t.id,
        )
        db.add(new_user)
        db.commit()
        f.write(f'CREADO: id={new_user.id}, tenant={new_user.tenant_id}\n')

db.close()
print('OK - ver _superadmin_fix.txt')
