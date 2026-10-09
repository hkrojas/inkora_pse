"""Narrow read model for the paginated fiscal-note list."""
import hashlib
from types import SimpleNamespace

from sqlalchemy import String, and_, func, or_
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import FunctionElement

import models
import schemas


class _Utf8Sha256(FunctionElement):
    type = String()
    inherit_cache = True


@compiles(_Utf8Sha256, "postgresql")
def _postgres_sha256(element, compiler, **kw):
    value = compiler.process(list(element.clauses)[0], **kw)
    return f"encode(sha256(convert_to({value}, 'UTF8')), 'hex')"


@compiles(_Utf8Sha256, "sqlite")
def _sqlite_sha256(element, compiler, **kw):
    value = compiler.process(list(element.clauses)[0], **kw)
    return f"inkora_sha256_hex({value})"


_COMPUTED = {
    "cliente", "source_quote", "nota_referencia", "document_number",
    "sunat_accepted", "has_sunat_xml", "has_sunat_cdr", "has_deliverable_fiscal_xml",
}


def _document_columns(model, contract, prefix):
    columns = [getattr(model, field).label(prefix + field)
               for field in contract.model_fields if field not in _COMPUTED]
    has_xml = or_(func.coalesce(model.sunat_xml_url, "") != "",
                  func.coalesce(model.sunat_xml_content, "") != "")
    has_cdr = or_(func.coalesce(model.sunat_cdr_url, "") != "",
                  func.coalesce(model.sunat_cdr_content, "") != "")
    return columns + [
        has_xml.label(prefix + "has_sunat_xml"),
        has_cdr.label(prefix + "has_sunat_cdr"),
        and_(has_cdr, func.coalesce(model.sunat_error, "") == "",
             func.coalesce(model.provider_verification_status, "").in_(["", "verified"])
             ).label(prefix + "sunat_accepted"),
    ]


def note_list_projection(query):
    if query.session.get_bind().dialect.name == "sqlite":
        # Local SQLite has no SHA-256 built-in. Register only on this connection;
        # production PostgreSQL uses its native function, without an extension.
        connection = query.session.connection().connection.driver_connection
        connection.create_function(
            "inkora_sha256_hex", 1,
            lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None,
            deterministic=True,
        )
    note = models.Cotizacion
    source = aliased(note)
    reference = aliased(note)
    client = aliased(models.Cliente)
    columns = _document_columns(note, schemas.FiscalNoteListResponse, "note_")
    columns += _document_columns(source, schemas.NoteReferenceDocumentListResponse, "source_")
    columns += _document_columns(reference, schemas.NoteReferenceDocumentListResponse, "reference_")
    columns += [getattr(client, field).label("client_" + field)
                for field in schemas.ClienteDocumentoListResponse.model_fields if field != "nombre"]
    columns += [
        (func.coalesce(note.sunat_xml_content, "") != "").label("has_xml_content"),
        _Utf8Sha256(note.sunat_xml_content).label("xml_digest"),
        note.provider_response["inkora_evidence"]["signed_xml_sha256"].label("evidence_digest"),
    ]
    return query.with_entities(*columns).outerjoin(client, and_(
        client.id == note.cliente_id, client.tenant_id == note.tenant_id,
    )).outerjoin(source, and_(
        source.id == note.source_quote_id, source.tenant_id == note.tenant_id,
    )).outerjoin(reference, and_(
        reference.id == note.nota_referencia_id, reference.tenant_id == note.tenant_id,
    ))


def note_list_response(row):
    values = dict(row._mapping)

    def document(prefix):
        data = {key.removeprefix(prefix): value for key, value in values.items() if key.startswith(prefix)}
        if data["id"] is None:
            return None
        data["document_number"] = models.Cotizacion.document_number.fget(SimpleNamespace(**data))
        return data

    data = document("note_")
    client = {key.removeprefix("client_"): value for key, value in values.items() if key.startswith("client_")}
    data.update(
        cliente=client if client["id"] is not None else None,
        source_quote=document("source_"),
        nota_referencia=document("reference_"),
        has_deliverable_fiscal_xml=bool(
            data["estado"] != "anulada" and data["provider_verification_status"] != "rejected"
            and values["has_xml_content"]
            and (values["evidence_digest"] == values["xml_digest"]
                 or (data["estado"] == "facturada" and data["has_sunat_cdr"]))
        ),
    )
    return schemas.FiscalNoteListResponse.model_validate(data)
