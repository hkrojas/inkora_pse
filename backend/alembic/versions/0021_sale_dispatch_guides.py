"""Add invoice-linked sale dispatches and GRE 09/31 traceability.

Revision ID: 0021_sale_dispatch_guides
Revises: 0020_tenant_fiscal_contingency
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0021_sale_dispatch_guides"
down_revision = "0020_tenant_fiscal_contingency"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("cotizaciones") as batch:
        batch.add_column(sa.Column("dispatch_reconciliation_status", sa.String(), nullable=False, server_default="required"))
        batch.add_column(sa.Column("dispatch_reconciliation_evidence", sa.JSON(), nullable=True))
    op.execute(
        "UPDATE cotizaciones SET dispatch_reconciliation_status = 'not_required' "
        "WHERE document_kind <> 'fiscal_document' OR tipo_comprobante <> '01'"
    )
    op.alter_column("cotizaciones", "dispatch_reconciliation_status", server_default="not_required")
    op.create_table(
        "sale_dispatches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("fiscal_document_id", sa.Integer(), sa.ForeignKey("cotizaciones.id"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("request_fingerprint", sa.String(), nullable=False),
        sa.Column("provisional_invoice_fingerprint", sa.String(), nullable=True),
        sa.Column("logistical_block_code", sa.String(), nullable=True),
        sa.Column("logistical_block_detail", sa.Text(), nullable=True),
        sa.Column("departure_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("departure_confirmed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_sale_dispatches_tenant_idempotency"),
        sa.CheckConstraint("version >= 1", name="ck_sale_dispatches_version_positive"),
    )
    op.create_index("ix_sale_dispatches_invoice_status", "sale_dispatches", ["tenant_id", "fiscal_document_id", "status"])

    op.create_table(
        "guide_external_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("issuer_ruc", sa.String(), nullable=False),
        sa.Column("series", sa.String(), nullable=False),
        sa.Column("number", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="manual"),
        sa.Column("verification_status", sa.String(), nullable=False, server_default="unverified"),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", "document_type", "issuer_ruc", "series", "number", name="uq_guide_external_reference_identity"),
    )
    op.create_index("ix_guide_external_reference_tenant_type", "guide_external_references", ["tenant_id", "document_type"])

    with op.batch_alter_table("guias_remision") as batch:
        batch.add_column(sa.Column("tipo_documento", sa.String(), nullable=False, server_default="09"))
        batch.add_column(sa.Column("dispatch_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("related_guide_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("external_gre_reference_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("goods_invoice_reference_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("freight_invoice_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("creation_idempotency_key", sa.String(), nullable=True))
        batch.add_column(sa.Column("fecha_entrega_transportista", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("indicador_m1_l", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("registrar_vehiculo_transportista", sa.Boolean(), nullable=False, server_default=sa.false()))
        for name in (
            "remitente_tipo_doc", "remitente_nro_doc", "remitente_razon_social",
            "destinatario_tipo_doc", "destinatario_nro_doc", "destinatario_razon_social",
            "pagador_flete_tipo", "pagador_tipo_doc", "pagador_nro_doc", "pagador_razon_social",
            "emission_environment",
        ):
            batch.add_column(sa.Column(name, sa.String(), nullable=True))
        batch.add_column(sa.Column("frozen_payload", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("frozen_xml", sa.Text(), nullable=True))
        batch.add_column(sa.Column("rejected_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key("fk_guias_dispatch", "sale_dispatches", ["dispatch_id"], ["id"])
        batch.create_foreign_key("fk_guias_related_guide", "guias_remision", ["related_guide_id"], ["id"])
        batch.create_foreign_key("fk_guias_external_gre", "guide_external_references", ["external_gre_reference_id"], ["id"])
        batch.create_foreign_key("fk_guias_external_invoice", "guide_external_references", ["goods_invoice_reference_id"], ["id"])
        batch.create_foreign_key("fk_guias_freight_invoice", "cotizaciones", ["freight_invoice_id"], ["id"])
        batch.create_index("ix_guias_remision_dispatch_id", ["dispatch_id"])
        batch.create_index("ix_guias_remision_related_guide_id", ["related_guide_id"])
        batch.create_unique_constraint("uq_guias_tenant_creation_idempotency", ["tenant_id", "creation_idempotency_key"])

    op.create_table(
        "sale_dispatch_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("dispatch_id", sa.Integer(), sa.ForeignKey("sale_dispatches.id"), nullable=False),
        sa.Column("fiscal_document_item_id", sa.Integer(), sa.ForeignKey("cotizacion_items.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("productos.id"), nullable=True),
        sa.Column("inventory_movement_id", sa.Integer(), sa.ForeignKey("inventory_movements.id"), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_code", sa.String(), nullable=False),
        sa.Column("product_code", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("confirmed_as_goods", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reservation_status", sa.String(), nullable=False, server_default="active"),
        sa.Column("reserved_at", sa.DateTime(), nullable=True),
        sa.Column("covered_at", sa.DateTime(), nullable=True),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("dispatch_id", "fiscal_document_item_id", name="uq_sale_dispatch_lines_invoice_line"),
        sa.CheckConstraint("quantity > 0", name="ck_sale_dispatch_lines_quantity_positive"),
    )
    op.create_index("ix_sale_dispatch_lines_availability", "sale_dispatch_lines", ["tenant_id", "fiscal_document_item_id", "reservation_status"])

    with op.batch_alter_table("guia_remision_items") as batch:
        batch.add_column(sa.Column("dispatch_line_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("fiscal_document_item_id", sa.Integer(), nullable=True))
        batch.alter_column("cantidad", type_=sa.Numeric(18, 4), existing_type=sa.Numeric(12, 2))
        batch.create_foreign_key("fk_guia_items_dispatch_line", "sale_dispatch_lines", ["dispatch_line_id"], ["id"])
        batch.create_foreign_key("fk_guia_items_invoice_line", "cotizacion_items", ["fiscal_document_item_id"], ["id"])
        batch.create_index("ix_guia_items_dispatch_line_id", ["dispatch_line_id"])
        batch.create_index("ix_guia_items_invoice_line_id", ["fiscal_document_item_id"])


def downgrade():
    with op.batch_alter_table("guia_remision_items") as batch:
        batch.drop_index("ix_guia_items_invoice_line_id")
        batch.drop_index("ix_guia_items_dispatch_line_id")
        batch.drop_constraint("fk_guia_items_invoice_line", type_="foreignkey")
        batch.drop_constraint("fk_guia_items_dispatch_line", type_="foreignkey")
        batch.drop_column("fiscal_document_item_id")
        batch.drop_column("dispatch_line_id")
    op.drop_index("ix_sale_dispatch_lines_availability", table_name="sale_dispatch_lines")
    op.drop_table("sale_dispatch_lines")
    with op.batch_alter_table("guias_remision") as batch:
        batch.drop_constraint("uq_guias_tenant_creation_idempotency", type_="unique")
        batch.drop_index("ix_guias_remision_related_guide_id")
        batch.drop_index("ix_guias_remision_dispatch_id")
        for constraint in ("fk_guias_freight_invoice", "fk_guias_external_invoice", "fk_guias_external_gre", "fk_guias_related_guide", "fk_guias_dispatch"):
            batch.drop_constraint(constraint, type_="foreignkey")
        for name in (
            "rejected_at", "frozen_xml", "frozen_payload", "emission_environment",
            "pagador_razon_social", "pagador_nro_doc", "pagador_tipo_doc", "pagador_flete_tipo",
            "destinatario_razon_social", "destinatario_nro_doc", "destinatario_tipo_doc",
            "remitente_razon_social", "remitente_nro_doc", "remitente_tipo_doc",
            "registrar_vehiculo_transportista", "indicador_m1_l", "fecha_entrega_transportista",
            "creation_idempotency_key", "version", "freight_invoice_id", "goods_invoice_reference_id", "external_gre_reference_id", "related_guide_id", "dispatch_id", "tipo_documento",
        ):
            batch.drop_column(name)
    op.drop_index("ix_guide_external_reference_tenant_type", table_name="guide_external_references")
    op.drop_table("guide_external_references")
    op.drop_index("ix_sale_dispatches_invoice_status", table_name="sale_dispatches")
    op.drop_table("sale_dispatches")
    with op.batch_alter_table("cotizaciones") as batch:
        batch.drop_column("dispatch_reconciliation_evidence")
        batch.drop_column("dispatch_reconciliation_status")
