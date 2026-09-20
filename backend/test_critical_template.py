from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
from decimal import Decimal

pytest.importorskip("slowapi")

from database import Base
import models
import crud
from services import calculations

# Base aislada por módulo: no depende de un test.db persistente ni del orden de la suite.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def critical_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        Base.metadata.drop_all(bind=engine)

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
def test_idor_lectura_ajena(critical_db):
    db = critical_db

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
def test_rollback_atomo_maestro_detalle(critical_db):
    db = critical_db
    tenant = models.Tenant(business_name="Rollback Co", business_ruc="20000000002")
    db.add(tenant)
    db.flush()
    user = models.User(
        email="rollback@test.com",
        rol="vendedor",
        hashed_password="X",
        tenant_id=tenant.id,
    )
    db.add(user)
    db.commit()
    
    # Simulamos enviar una cotización con un item corrupto que hará fallar el commit parcial
    # Para la prueba, omitimos detalles largos, pero el objetivo es asegurar que 
    # si ocurre una excepción en la creación, el rollback limpia la DB.
    try:
        # Inyectamos una cotización sin cliente válido (Foreign Key failed)
        falla = models.Cotizacion(
            usuario_id=user.id,
            tenant_id=tenant.id,
            cliente_id=99999,
        )
        db.add(falla)
        db.commit()
    except Exception:
        db.rollback()
    
    # Verificamos que no quedó colgada parcialmente en la sesión o BD
    búsqueda = db.query(models.Cotizacion).filter(models.Cotizacion.cliente_id == 99999).first()
    assert búsqueda is None, "La transacción no hizo rollback adecuadamente"
