"""Synthetic fiscal-note benchmark; only a dedicated local inkora_read_* DB."""
import argparse
from datetime import datetime
import hashlib
import json
from types import SimpleNamespace
import uuid

from benchmark_read_egress import measure, old_module
import conftest
import models
import schemas
from database import Base
from routers import facturacion
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    url = make_url(args.url)
    if (not url.drivername.startswith("postgresql") or url.host not in {"127.0.0.1", "localhost", "::1"}
            or not (url.database or "").startswith("inkora_read_")):
        raise SystemExit("Requires local disposable inkora_read_* database")
    schema = "note_benchmark_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base.metadata.create_all(engine)
        with Session(engine, expire_on_commit=False) as db:
            tenant = conftest.make_tenant(db, "NBNCH")
            user = conftest.make_user(db, tenant, email="note-benchmark@test.local")
            client = conftest.make_cliente(db, tenant, "NBNCH", numero_documento="20123456781")
            scope = SimpleNamespace(id=user.id, tenant_id=tenant.id, rol=user.rol, is_superadmin=False)
            xml = "áñ" * 25000
            common = dict(tenant_id=tenant.id, usuario_id=user.id, cliente_id=client.id,
                fecha_emision=datetime(2026, 9, 10), sunat_xml_content=xml, sunat_cdr_content="c" * 50000,
                provider_response={"large": "p" * 50000,
                    "inkora_evidence": {"signed_xml_sha256": hashlib.sha256(xml.encode()).hexdigest()}},
                sunat_qr_svg="q" * 50000, total_venta=118, total_gravada=100, total_igv=18)
            source = models.Cotizacion(**common, serie="COT", correlativo=1, document_kind="quotation", tipo_comprobante="00")
            reference = models.Cotizacion(**common, serie="F001", correlativo=1, document_kind="fiscal_document", tipo_comprobante="01")
            db.add_all([source, reference])
            db.flush()
            for i in range(100):
                db.add(models.Cotizacion(**common, serie="FC01", correlativo=i+1, document_kind="credit_note", tipo_comprobante="07",
                    estado="pendiente", provider_verification_status="pending_confirmation",
                    source_quote_id=source.id, nota_referencia_id=reference.id))
            db.commit()
            baseline = "0298d26ec08ccaec4bbabfacab788b8c1aed7b2e"
            legacy = old_module("backend/routers/facturacion.py", baseline)
            def run(function, limit):
                result = function(db=db, current_user=scope, skip=0, limit=limit,
                    tipo_nota=None, tab="all", estado=None, desde=None, hasta=None, q=None)
                return schemas.FiscalNotePageResponse.model_validate(result).model_dump(mode="json")
            results = {}
            for limit in (15, 100):
                before, old_metrics = measure(db, lambda: run(legacy.list_notas_page, limit))
                after, new_metrics = measure(db, lambda: run(facturacion.list_notas_page, limit))
                assert before == after
                results[str(limit)] = {"before": old_metrics, "after": new_metrics}
            statements = []
            def capture(conn, cursor, statement, parameters, context, executemany):
                if statement.lstrip().upper().startswith("SELECT"):
                    statements.append((statement, parameters))
            event.listen(engine, "before_cursor_execute", capture)
            try:
                run(facturacion.list_notas_page, 15)
            finally:
                event.remove(engine, "before_cursor_execute", capture)
            plans = [db.connection().exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, params).scalar()[0]
                     for sql, params in statements]
            print(json.dumps({"baseline": baseline, "synthetic_notes": 100,
                "note": "Decoded SQL result-value bytes, not billable egress. Three local warm repetitions.",
                "pages": results, "plans": plans}, indent=2))
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        admin.dispose()


if __name__ == "__main__":
    main()
