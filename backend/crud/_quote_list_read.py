"""Scalar read model: list serialization must never load ORM relationships."""
from types import SimpleNamespace

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import aliased

import models
import schemas


def quote_list_projection(query):
    quote = models.Cotizacion
    client = aliased(models.Cliente)
    candidate = aliased(quote)
    linked = aliased(quote)
    latest_id = select(func.max(candidate.id)).where(
        candidate.source_quote_id == quote.id,
        candidate.tenant_id == quote.tenant_id,
        candidate.document_kind == "fiscal_document",
        or_(candidate.estado.is_(None), candidate.estado != "anulada"),
        quote.document_kind == "quotation",
    ).correlate(quote).scalar_subquery()
    computed = {"cliente", "document_number", "payment_status", "sunat_accepted",
                "has_sunat_xml", "has_sunat_cdr", "linked_fiscal_document_id",
                "linked_fiscal_document_number", "linked_fiscal_document_status"}
    columns = [getattr(quote, field) for field in schemas.CotizacionListResponse.model_fields
               if field not in computed]
    has_xml = or_(func.coalesce(quote.sunat_xml_url, "") != "",
                  func.coalesce(quote.sunat_xml_content, "") != "")
    has_cdr = or_(func.coalesce(quote.sunat_cdr_url, "") != "",
                  func.coalesce(quote.sunat_cdr_content, "") != "")
    columns += [quote.tenant_id, has_xml.label("has_sunat_xml"), has_cdr.label("has_sunat_cdr"),
                and_(has_cdr, func.coalesce(quote.sunat_error, "") == "",
                     func.coalesce(quote.provider_verification_status, "").in_(["", "verified"])
                     ).label("sunat_accepted"),
                linked.id.label("linked_fiscal_document_id"),
                linked.estado.label("linked_fiscal_document_status"),
                linked.serie.label("linked_serie"), linked.correlativo.label("linked_correlativo")]
    columns += [getattr(client, field).label("client_" + field)
                for field in schemas.ClienteResponse.model_fields]
    return query.with_entities(*columns).outerjoin(client, and_(
        client.id == quote.cliente_id, client.tenant_id == quote.tenant_id,
    )).outerjoin(linked, linked.id == latest_id)


def quote_list_item(row):
    values = dict(row._mapping)
    client = {field: values.pop("client_" + field) for field in schemas.ClienteResponse.model_fields}
    values["cliente"] = SimpleNamespace(**client) if client["id"] is not None else None
    linked = SimpleNamespace(serie=values.pop("linked_serie"), correlativo=values.pop("linked_correlativo"))
    values["linked_fiscal_document_number"] = models.Cotizacion.document_number.fget(linked)
    item = SimpleNamespace(**values)
    item.document_number = models.Cotizacion.document_number.fget(item)
    item.payment_status = models.Cotizacion.payment_status.fget(item)
    return item
