"""set_fake_token.py"""
import sys; sys.path.insert(0,'.')
from database import SessionLocal
import models
db = SessionLocal()
t = db.query(models.Tenant).filter(models.Tenant.id==6).first()
t.apisperu_token = "fake-token-for-load-testing"
db.commit()
print(f"Set fake token on tenant {t.business_name}")
db.close()
