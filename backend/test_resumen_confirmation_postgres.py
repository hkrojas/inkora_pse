"""Concurrency checks on an exclusive disposable loopback inkora_summary_* DB."""
from concurrent.futures import ThreadPoolExecutor
import os
from threading import Barrier, Event

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import crud
import models
from database import Base
from test_resumen_confirmation import _cdr, _payload, _result


@pytest.fixture(scope="module")
def summary_pg_factory():
    value = os.getenv("INKORA_SUMMARY_POSTGRES_URL", "")
    if not value:
        if os.getenv("INKORA_REQUIRE_POSTGRES_TESTS") == "1":
            pytest.fail("INKORA_SUMMARY_POSTGRES_URL es obligatoria")
        pytest.skip("PostgreSQL local de resumen no configurado")
    url = make_url(value)
    assert url.drivername.startswith("postgresql")
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    assert (url.database or "").startswith("inkora_summary_")
    engine = create_engine(value)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.parametrize("code, late_response", [("0", "pending"), ("0", "timeout"),
                                                ("2335", "pending"), ("2335", "timeout")])
def test_concurrent_late_consultation_cannot_regress_confirmed_summary(summary_pg_factory, code, late_response):
    with summary_pg_factory() as db:
        tenant = db.query(models.Tenant).filter(models.Tenant.business_ruc == "20123456789").first()
        if tenant is None:
            tenant = models.Tenant(business_name="Synthetic summary concurrency", business_ruc="20123456789")
            db.add(tenant)
            db.commit()
        row = crud.create_resumen_diario(db, tenant_id=tenant.id, usuario_id=None, payload=_payload())
        tenant_id, summary_id = tenant.id, row.id
    loaded = Barrier(2)
    confirmed = Event()

    def finish_first():
        with summary_pg_factory() as db:
            db.get(models.ResumenDiario, summary_id)
            loaded.wait(timeout=10)
            try:
                if code == "0":
                    crud.mark_resumen_diario_sent(db, summary_id, result=_result({"cdr": _cdr()}), tenant_id=tenant_id)
                else:
                    crud.mark_resumen_diario_rejected(db, summary_id, error="SUNAT 2335", tenant_id=tenant_id,
                                                     provider_response={"cdr": _cdr(code=code)})
            finally:
                confirmed.set()

    def finish_late():
        with summary_pg_factory() as db:
            stale = db.get(models.ResumenDiario, summary_id)
            assert stale.status == "pending"
            loaded.wait(timeout=10)
            assert confirmed.wait(timeout=10)
            if late_response == "pending":
                crud.mark_resumen_diario_sent(db, summary_id, result=_result({"estado": 202}), tenant_id=tenant_id)
            else:
                crud.mark_resumen_diario_rejected(db, summary_id, error="Timeout", tenant_id=tenant_id, pending=True)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(finish_first)
        second = executor.submit(finish_late)
        first.result(timeout=20)
        second.result(timeout=20)
    with summary_pg_factory() as db:
        saved = db.get(models.ResumenDiario, summary_id)
        assert saved.status == ("sent" if code == "0" else "rejected")
        assert saved.success is (code == "0")
