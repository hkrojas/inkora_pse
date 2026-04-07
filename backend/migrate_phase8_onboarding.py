"""
migrate_phase8_onboarding.py — Fase 8: Onboarding Acceleration

Migraciones idempotentes para preparar la base de datos existente
para las nuevas funcionalidades de onboarding.

Tareas:
  1. Asegurar que todos los tenants existentes tengan un registro Subscription.
     (Los nuevos tenants ya se crean con Subscription auto, pero los existentes no.)

Uso:
    cd backend
    python migrate_phase8_onboarding.py

Seguro de ejecutar múltiples veces (idempotente).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, engine, Base
import models


def run_migration():
    print("=== Migración Fase 8: Onboarding ===\n")

    # Crear tablas nuevas si no existen (seguro en dev; en prod usar alembic)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        tenants = db.query(models.Tenant).all()
        print(f"Tenants encontrados: {len(tenants)}")

        creados = 0
        ya_existian = 0

        for tenant in tenants:
            existing_sub = (
                db.query(models.Subscription)
                .filter(models.Subscription.tenant_id == tenant.id)
                .first()
            )
            if existing_sub:
                ya_existian += 1
                continue

            # Crear Subscription en estado trial para el tenant existente
            sub = models.Subscription(
                tenant_id=tenant.id,
                status=models.SUBSCRIPTION_STATUS_TRIAL,
                onboarding_status=models.ONBOARDING_STATUS_NOT_STARTED,
            )
            db.add(sub)
            creados += 1
            print(f"  [CREADO] Subscription para tenant id={tenant.id} ({tenant.business_name})")

        db.commit()

        print(f"\nResultado:")
        print(f"  Subscriptions ya existentes : {ya_existian}")
        print(f"  Subscriptions creadas       : {creados}")
        print("\n=== Migración completada ===")

    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
