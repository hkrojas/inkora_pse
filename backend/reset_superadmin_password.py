"""reset_superadmin_password.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from security import get_password_hash

db = SessionLocal()

NEW_PASSWORD = "superadmin123"

# Reset superadmin
u = db.query(models.User).filter(models.User.email == "admin@printflow.pe").first()
if u:
    u.hashed_password = get_password_hash(NEW_PASSWORD)
    db.commit()
    print(f"Superadmin password reseteada: {NEW_PASSWORD}")
else:
    print("Superadmin no encontrado")

# Reset vendedor default
u2 = db.query(models.User).filter(models.User.email == "usuario@printflow.pe").first()
if u2:
    u2.hashed_password = get_password_hash(NEW_PASSWORD)
    db.commit()
    print(f"Vendedor password reseteada: {NEW_PASSWORD}")
else:
    print("Vendedor no encontrado")

db.close()
