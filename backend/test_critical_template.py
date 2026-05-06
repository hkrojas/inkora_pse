from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest
from decimal import Decimal

pytest.importorskip("slowapi")

# Import your FastAPI app and models
from main import app
from database import get_db
from database import Base
import models
import crud
import schemas
from services import calculations

# Setup Test Database (SQLite in-memory)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ========================================================
# 1. TEST DE PRECISIÓN NUMÉRICA (CÁLCULO SUNAT)
# ========================================================
def test_calculo_redondeo_sunat():
    # Precio con muchos decimales o impar: 10.33 * 3 = 30.99
    # Base imponible debería ser 30.99 / 1.18 = 26.2627 -> Redondeado 26.26
    # IGV = 30.99 - 26.26 = 4.73
    precio_final = Decimal("10.33")
    cantidad = Decimal("3.00")
    
    calc = calculations.calcular_item(cantidad, precio_final)
    
    assert calc["total_item"] == Decimal("30.99")
    assert calc["total_base_igv"] == Decimal("26.26")
    assert calc["total_igv"] == Decimal("4.73")
    
    # La suma estricta de base e IGV debe igualar el Total de la línea
    assert calc["total_base_igv"] + calc["total_igv"] == calc["total_item"]

# ========================================================
# 2. TEST DE IDOR (INSECURE DIRECT OBJECT REFERENCE)
# ========================================================
def test_idor_lectura_ajena():
    db = TestingSessionLocal()

    # Limpiar datos previos de este test para evitar UNIQUE violations en reruns
    for email in ["a@test.com", "b@test.com"]:
        existing = db.query(models.User).filter_by(email=email).first()
        if existing:
            db.delete(existing)
    db.flush()

    # Tenant requerido (tenant_id NOT NULL en User y Cotizacion) — get-or-create
    tenant = db.query(models.Tenant).filter_by(business_ruc="20000000001").first()
    if not tenant:
        tenant = models.Tenant(business_name="Test Co", business_ruc="20000000001")
        db.add(tenant)
        db.flush()

    # Dos usuarios del mismo tenant, ambos rol vendedor
    user_A = models.User(email="a@test.com", rol="vendedor", hashed_password="X", tenant_id=tenant.id)
    user_B = models.User(email="b@test.com", rol="vendedor", hashed_password="X", tenant_id=tenant.id)
    db.add_all([user_A, user_B])
    db.flush()

    # Cotizacion pertenece a user_A (mismo tenant)
    cotiz = models.Cotizacion(
        usuario_id=user_A.id,
        tenant_id=tenant.id,
        total_venta=100.00,
    )
    db.add(cotiz)
    db.commit()

    # user_B (vendedor) no debe poder leer cotizaciones de user_A
    resultado = crud.get_cotizacion(db, cotizacion_id=cotiz.id, usuario=user_B)
    assert resultado is None, "Vulnerabilidad IDOR: user_B puede leer cotizaciones de user_A"

    # user_A sí debe poder leer la suya
    resultado_ok = crud.get_cotizacion(db, cotizacion_id=cotiz.id, usuario=user_A)
    assert resultado_ok is not None

# ========================================================
# 3. TEST TRANSACTIONAL (ATOMIC SUCCESS AND FAIL)
# ========================================================
def test_rollback_atomo_maestro_detalle():
    db = TestingSessionLocal()
    user = db.query(models.User).first()
    
    # Simulamos enviar una cotización con un item corrupto que hará fallar el commit parcial
    # Para la prueba, omitimos detalles largos, pero el objetivo es asegurar que 
    # si ocurre una excepción en la creación, el rollback limpia la DB.
    try:
        from sqlalchemy.exc import IntegrityError
        # Inyectamos una cotización sin cliente válido (Foreign Key failed)
        falla = models.Cotizacion(usuario_id=user.id, cliente_id=99999) # 9999 no existe
        db.add(falla)
        db.commit()
    except Exception:
        db.rollback()
    
    # Verificamos que no quedó colgada parcialmente en la sesión o BD
    db_test = TestingSessionLocal()
    búsqueda = db_test.query(models.Cotizacion).filter(models.Cotizacion.cliente_id == 99999).first()
    assert búsqueda is None, "La transacción no hizo rollback adecuadamente"
