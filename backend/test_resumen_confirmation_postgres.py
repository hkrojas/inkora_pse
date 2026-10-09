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


def test_concurrent_manual_and_automatic_rc_share_one_counter_namespace(summary_pg_factory):
    from services import emission_queue_service as queue, void_recovery_service as recovery
    from test_void_recovery import accepted_document
    with summary_pg_factory() as db:
        tenant, user, document = accepted_document(db, "SUMRACE1")
        payload = recovery.prepare_snapshot(db, document, user, "No otorgado")["void_payload"]
        tenant_id, user_id, document_id = tenant.id, user.id, document.id
    start = Barrier(2)

    def automatic():
        with summary_pg_factory() as db:
            user, document = db.get(models.User, user_id), db.get(models.Cotizacion, document_id)
            start.wait(timeout=10)
            job, _ = queue.enqueue_void_document_job(db, document, user, motivo="No otorgado")
            return job.payload_snapshot["void_payload"]["correlativo"]

    def manual():
        with summary_pg_factory() as db:
            start.wait(timeout=10)
            try:
                recovery.ensure_manual_batch_available(db, tenant_id, payload)
                return crud.create_resumen_diario(db, tenant_id=tenant_id, usuario_id=user_id, payload=payload).correlativo
            except ValueError:
                db.rollback()
                return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        automated, manually = executor.submit(automatic), executor.submit(manual)
        auto_counter, manual_counter = automated.result(timeout=20), manually.result(timeout=20)
    assert auto_counter != manual_counter
    if manual_counter:
        assert manual_counter == payload["correlativo"]
        assert int(auto_counter.split("-")[-1]) == int(manual_counter.split("-")[-1]) + 1


def test_concurrent_manual_aliases_cannot_reserve_the_same_numeric_counter_twice(summary_pg_factory):
    from services import void_recovery_service as recovery
    from test_void_recovery import accepted_document
    with summary_pg_factory() as db:
        tenant, user, document = accepted_document(db, "SUMRACE2")
        payload = recovery.prepare_snapshot(db, document, user, "No otorgado")["void_payload"]
        tenant_id, user_id = tenant.id, user.id
    day, counter = payload["correlativo"].split("-")
    aliases = [f"{day}-{int(counter)}", f"{day}-{int(counter):05d}"]
    start = Barrier(2)

    def reserve(value):
        with summary_pg_factory() as db:
            candidate = dict(payload, correlativo=value)
            start.wait(timeout=10)
            try:
                recovery.ensure_manual_batch_available(db, tenant_id, candidate)
                crud.create_resumen_diario(db, tenant_id=tenant_id, usuario_id=user_id, payload=candidate)
                return True
            except ValueError:
                db.rollback()
                return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, aliases))
    assert sorted(results) == [False, True]
    with summary_pg_factory() as db:
        assert db.query(models.ResumenDiario).filter_by(tenant_id=tenant_id).count() == 1
