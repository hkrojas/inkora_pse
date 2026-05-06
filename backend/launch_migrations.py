"""Orden canónico de migraciones del backend Inkora para launch/staging."""

from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent

LAUNCH_MIGRATION_SCRIPTS = (
    "migrate_multitenancy.py",
    "migrate_auth_passwords.py",
    "migrate_fases_1_7.py",
    "migrate_note_reason_fields.py",
    "migrate_gre_credentials.py",
    "migrate_gre_extended_fields.py",
    "migrate_pagos.py",
    "migrate_document_flow_phase4.py",
    "migrate_saas_phase5.py",
    "migrate_emission_jobs.py",
    "migrate_emission_reliability.py",
    "migrate_phase6_launch_polish.py",
    "migrate_phase9_beta.py",
    "migrate_phase8_onboarding.py",
    "migrate_analytics.py",
    "migrate_fiscal_pdf_artifacts.py",
    "migrate_productos_moneda.py",
    "migrate_cobranza_indexes.py",
    "migrate_cotizacion_item_codigo_producto.py",
    "migrate_cotizacion_cuotas_pago.py",
    "migrate_guias_cliente_id.py",
    "migrate_resumenes_diarios.py",
    "migrate_reversiones_fiscales.py",
    "migrate_retenciones_fiscales.py",
    "migrate_percepciones_fiscales.py",
)


def iter_launch_migration_paths():
    for script_name in LAUNCH_MIGRATION_SCRIPTS:
        yield BACKEND_DIR / script_name
