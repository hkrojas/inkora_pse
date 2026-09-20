"""
seed_demo_tenant.py — Fase 8: Onboarding Acceleration

Script de siembra de datos de demostración para un tenant nuevo.
Útil para validar el flujo completo antes de onboardear un cliente real.

Uso:
    cd backend
    # Definir una contraseña sintética de al menos 12 caracteres.
    # PowerShell: $env:INKORA_DEMO_ADMIN_PASSWORD = "..."
    python seed_demo_tenant.py

El script crea (si no existe):
  - Un Tenant demo con RUC ficticio
  - Un User admin con credenciales conocidas
  - 5 clientes de ejemplo
  - 8 productos/servicios de ejemplo
  - 1 cotización de muestra

Nota: El propio script bloquea entornos no locales y bases que no sean SQLite.
"""

import os
import sys
from datetime import datetime

# Asegurar que el directorio del script esté en el path
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, engine, Base
from config import settings
from security import get_password_hash
import models
import schemas
import crud

# ---------------------------------------------------------------------------
# Configuración del tenant demo
# ---------------------------------------------------------------------------

DEMO_RUC = "20999999999"
DEMO_BUSINESS_NAME = "Imprenta Demo Inkora SAC"
DEMO_ADMIN_EMAIL = os.getenv("INKORA_DEMO_ADMIN_EMAIL", "admin@demo.inkora.pe")
DEMO_ADMIN_PASSWORD = os.getenv("INKORA_DEMO_ADMIN_PASSWORD", "")

DEMO_CLIENTES = [
    {
        "tipo_documento": "6",
        "numero_documento": "20100100100",
        "razon_social": "Cliente Corporativo SAC",
        "nombre_comercial": "Corp SAC",
        "direccion": "Av. Javier Prado 1234, San Isidro",
        "email": "compras@corporativo.pe",
        "telefono": "987654310",
        "whatsapp": "987654321",
        "contacto": "Carlos Mendes",
        "condicion_pago": "credito_30",
        "observaciones": "Paga puntual. Requiere factura siempre.",
    },
    {
        "tipo_documento": "6",
        "numero_documento": "20200200200",
        "razon_social": "Distribuidora Norte EIRL",
        "nombre_comercial": "DistriNorte",
        "direccion": "Jr. Callao 567, Breña",
        "email": "norte@distribuidora.pe",
        "telefono": "987654311",
        "condicion_pago": "contado",
    },
    {
        "tipo_documento": "6",
        "numero_documento": "20300300300",
        "razon_social": "Supermercados Lima SA",
        "direccion": "Av. La Marina 890, San Miguel",
        "email": "compras@superlima.pe",
        "condicion_pago": "credito_15",
    },
    {
        "tipo_documento": "1",
        "numero_documento": "12345678",
        "razon_social": "García Pérez Juan Carlos",
        "email": "juan.garcia@gmail.com",
        "telefono": "987000001",
        "condicion_pago": "contado",
    },
    {
        "tipo_documento": "1",
        "numero_documento": "87654321",
        "razon_social": "Torres Mamani Ana",
        "email": "ana.torres@outlook.com",
        "telefono": "987000002",
    },
]

DEMO_PRODUCTOS = [
    {
        "nombre": "Impresión A4 Full Color",
        "descripcion": "Impresión a color en papel couché 90gr tamaño A4",
        "precio_unitario": "5.90",
        "codigo_interno": "IMP-A4-FC",
        "unidad_medida": "NIU",
        "tipo_afectacion_igv": "10",
    },
    {
        "nombre": "Impresión A3 Full Color",
        "descripcion": "Impresión a color en papel couché 90gr tamaño A3",
        "precio_unitario": "9.50",
        "codigo_interno": "IMP-A3-FC",
        "unidad_medida": "NIU",
        "tipo_afectacion_igv": "10",
    },
    {
        "nombre": "Plastificado Mate A4",
        "descripcion": "Laminado mate de alta calidad tamaño A4",
        "precio_unitario": "2.50",
        "codigo_interno": "PLAST-MAT-A4",
        "unidad_medida": "NIU",
        "tipo_afectacion_igv": "10",
    },
    {
        "nombre": "Plastificado Brillante A4",
        "descripcion": "Laminado brillante tamaño A4",
        "precio_unitario": "2.50",
        "codigo_interno": "PLAST-BRIL-A4",
        "unidad_medida": "NIU",
        "tipo_afectacion_igv": "10",
    },
    {
        "nombre": "Diseño Gráfico",
        "descripcion": "Servicio de diseño gráfico por pieza (arte simple)",
        "precio_unitario": "50.00",
        "codigo_interno": "DIS-GFX",
        "unidad_medida": "ZZ",
        "tipo_afectacion_igv": "10",
    },
    {
        "nombre": "Troquelado Especial",
        "descripcion": "Troquelado en forma personalizada por millar",
        "precio_unitario": "80.00",
        "codigo_interno": "TROQ-ESP",
        "unidad_medida": "MLL",
        "tipo_afectacion_igv": "10",
    },
    {
        "nombre": "Impresión Tarjeta Personal (Millar)",
        "descripcion": "1000 tarjetas personales full color 2 caras, 350gr",
        "precio_unitario": "120.00",
        "codigo_interno": "TARJ-1MIL",
        "unidad_medida": "MLL",
        "tipo_afectacion_igv": "10",
    },
    {
        "nombre": "Impresión Banner 1x2m",
        "descripcion": "Banner gigantografía 1m x 2m en lona 13oz",
        "precio_unitario": "45.00",
        "codigo_interno": "BAN-1X2",
        "unidad_medida": "NIU",
        "tipo_afectacion_igv": "10",
    },
]


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------

def validate_demo_seed_target(environment: str, database_url: str, password: str) -> None:
    normalized_environment = str(environment or "").strip().lower()
    normalized_database_url = str(database_url or "").strip().lower()
    if normalized_environment not in {"local", "development", "dev", "test"}:
        raise RuntimeError("El seed demo solo puede ejecutarse en un entorno local o test.")
    if not normalized_database_url.startswith("sqlite"):
        raise RuntimeError("El seed demo solo admite una base SQLite local y desechable.")
    if len(password) < 12:
        raise RuntimeError(
            "INKORA_DEMO_ADMIN_PASSWORD es obligatoria y debe tener al menos 12 caracteres."
        )


def main():
    validate_demo_seed_target(
        settings.ENVIRONMENT,
        settings.DATABASE_URL,
        DEMO_ADMIN_PASSWORD,
    )
    print("=== Seed Demo Tenant — Inkora Fase 8 ===\n")

    # Crear tablas si no existen (solo para dev)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Tenant
        existing_tenant = crud.get_tenant_by_ruc(db, DEMO_RUC)
        if existing_tenant:
            tenant = existing_tenant
            print(f"[OK] Tenant existente: {tenant.business_name} (id={tenant.id})")
        else:
            tenant_data = schemas.TenantCreate(
                business_name=DEMO_BUSINESS_NAME,
                business_ruc=DEMO_RUC,
                business_address="Av. Demo 123, Lima, Lima",
                business_phone="999999999",
            )
            tenant = crud.create_tenant(db, tenant_data)
            print(f"[CREADO] Tenant: {tenant.business_name} (id={tenant.id})")

        # 2. Usuario admin
        existing_user = crud.get_user_by_email(db, DEMO_ADMIN_EMAIL)
        if existing_user:
            user = existing_user
            print(f"[OK] Usuario existente: {user.email}")
        else:
            user = models.User(
                email=DEMO_ADMIN_EMAIL,
                hashed_password=get_password_hash(DEMO_ADMIN_PASSWORD),
                nombre_completo="Admin Demo Inkora",
                rol="admin",
                tenant_id=tenant.id,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[CREADO] Usuario admin sintético: {user.email}")

        # 3. Establecimiento fiscal sintético. Las pruebas de navegador no
        # consultan proveedores externos; simulan el snapshot que Factiliza
        # persistiría para una empresa real.
        demo_establishment = (
            db.query(models.TenantEstablishment)
            .filter(
                models.TenantEstablishment.tenant_id == tenant.id,
                models.TenantEstablishment.sunat_code == "0000",
            )
            .first()
        )
        if not demo_establishment:
            demo_establishment = models.TenantEstablishment(
                tenant_id=tenant.id,
                sunat_code="0000",
                name="Establecimiento principal",
                ubigeo="150101",
                address="Av. Demo 123, Lima, Lima",
                is_main=True,
                is_active=True,
                verified_at=datetime.now(),
                verified_by_user_id=user.id,
                verification_note="Snapshot SUNAT sintético para pruebas locales aisladas.",
            )
            db.add(demo_establishment)
            db.commit()
            print("[CREADO] Establecimiento fiscal sintético: 0000")

        # 4. Clientes
        clientes_creados = 0
        for c_data in DEMO_CLIENTES:
            existing = (
                db.query(models.Cliente)
                .filter(
                    models.Cliente.tenant_id == tenant.id,
                    models.Cliente.numero_documento == c_data["numero_documento"],
                )
                .first()
            )
            if existing:
                continue
            cliente_schema = schemas.ClienteCreate(**c_data)
            crud.create_cliente(db, cliente_schema, tenant.id)
            clientes_creados += 1

        print(f"[CLIENTES] {clientes_creados} creados ({len(DEMO_CLIENTES) - clientes_creados} ya existían)")

        # 5. Productos
        from decimal import Decimal
        productos_creados = 0
        for p_data in DEMO_PRODUCTOS:
            existing = (
                db.query(models.Producto)
                .filter(
                    models.Producto.tenant_id == tenant.id,
                    models.Producto.nombre == p_data["nombre"],
                )
                .first()
            )
            if existing:
                continue
            p_schema = schemas.ProductoCreate(
                nombre=p_data["nombre"],
                descripcion=p_data.get("descripcion"),
                precio_unitario=Decimal(p_data["precio_unitario"]),
                codigo_interno=p_data.get("codigo_interno"),
                unidad_medida=p_data.get("unidad_medida", "NIU"),
                tipo_afectacion_igv=p_data.get("tipo_afectacion_igv", "10"),
            )
            crud.create_producto(db, p_schema, tenant.id)
            productos_creados += 1

        print(f"[PRODUCTOS] {productos_creados} creados ({len(DEMO_PRODUCTOS) - productos_creados} ya existían)")

        # 6. Cotización de muestra
        primer_cliente = (
            db.query(models.Cliente)
            .filter(models.Cliente.tenant_id == tenant.id)
            .first()
        )
        primer_producto = (
            db.query(models.Producto)
            .filter(models.Producto.tenant_id == tenant.id)
            .first()
        )

        cotizacion_existente = (
            db.query(models.Cotizacion)
            .filter(
                models.Cotizacion.tenant_id == tenant.id,
                models.Cotizacion.document_kind == "quotation",
            )
            .first()
        )

        if not cotizacion_existente and primer_cliente and primer_producto:
            cot_schema = schemas.CotizacionCreate(
                cliente_id=primer_cliente.id,
                moneda="PEN",
                tipo_comprobante="00",
                observaciones="Cotización de muestra generada por seed demo",
                items=[
                    schemas.CotizacionItemCreate(
                        descripcion=primer_producto.nombre,
                        cantidad=Decimal("10"),
                        precio_unitario=primer_producto.precio_unitario,
                        unidad_medida=primer_producto.unidad_medida,
                        tipo_afectacion_igv=primer_producto.tipo_afectacion_igv,
                    )
                ],
            )
            cot = crud.create_cotizacion(db, cot_schema, user.id, tenant.id)
            print(f"[COTIZACION] Muestra creada: COT-{str(cot.correlativo).zfill(6)}")
        elif cotizacion_existente:
            print(f"[OK] Cotización de muestra ya existe")
        else:
            print(f"[SKIP] No se pudo crear cotización (falta cliente o producto)")

        print("\n=== Seed completado ===")
        print(f"  Tenant ID  : {tenant.id}")
        print(f"  Email      : {DEMO_ADMIN_EMAIL}")
        print("  Contraseña : configurada mediante variable de entorno")
        print(f"  RUC        : {DEMO_RUC}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
