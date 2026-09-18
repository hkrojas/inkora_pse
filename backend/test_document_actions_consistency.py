from datetime import datetime

import pytest
import models
import schemas
from routers.facturacion import _fiscal_doc_counts, _fiscal_doc_tab_filter
from services.fiscal_presentation_service import presentation_status
from services.document_actions_service import available_actions
from test_document_actions_recovery import client_for
from test_emission_queue import _make_fiscal_document


@pytest.mark.parametrize('state,error,verification,cdr,expected', [
    ('anulada', '3127', None, 'cdr', 'voided'),
    ('anulada', None, 'pending_confirmation', 'cdr', 'voided'),
    ('borrador', None, None, None, 'draft'),
    ('pendiente', '[1033] ya informado', None, None, 'pending_confirmation'),
    ('pendiente', None, 'pending_confirmation', None, 'pending_confirmation'),
    ('pendiente', '[0111] policy', None, None, 'rejected'),
    ('pendiente', None, 'unverified', 'cdr', 'pending'),
    ('facturada', '', 'verified', 'cdr', 'emitted'),
    ('facturada', None, None, 'cdr', 'emitted'),
    ('pendiente', None, None, None, 'pending'),
])
def test_filter_schema_and_actions_agree(db_session, state, error, verification, cdr, expected):
    _, user, doc = _make_fiscal_document(db_session, 'AC1')
    doc.estado, doc.sunat_error = state, error
    doc.provider_verification_status, doc.sunat_cdr_content = verification, cdr
    db_session.commit()
    base = db_session.query(models.Cotizacion).filter_by(id=doc.id)
    counts = _fiscal_doc_counts(base)
    assert counts['all'] == sum(value for key, value in counts.items() if key != 'all') == 1
    tab = 'pending' if expected == 'pending_confirmation' else expected
    assert base.filter(_fiscal_doc_tab_filter(tab)).count() == 1
    assert presentation_status(doc) == schemas.FiscalDocumentListResponse.model_validate(doc).fiscal_status == expected
    actions = available_actions(db_session, doc, user)
    assert actions['fiscal_status'] == expected
    if expected != 'emitted':
        assert not any(actions[key] for key in ('void', 'credit_note', 'debit_note', 'create_guide'))


def test_search_and_pagination_reach_beyond_first_hundred(db_session):
    _, user, doc = _make_fiscal_document(db_session, 'AC2')
    doc.correlativo = 987654
    doc.condicion_pago = 'credito_15'
    doc.serie = 'FA01'
    db_session.add_all([models.Cotizacion(
        tenant_id=doc.tenant_id, usuario_id=user.id, cliente_id=doc.cliente_id,
        serie='FA01', correlativo=i, fecha_emision=datetime(2026, 9, 18),
        estado='pendiente', document_kind='fiscal_document', tipo_comprobante='01',
        total_gravada=10, total_igv=1.8, total_venta=11.8, moneda='PEN', condicion_pago='contado',
    ) for i in range(1, 185)])
    db_session.commit()
    client = client_for(db_session, user)
    page = client.get('/facturas-emitidas/page?skip=180&limit=15').json()
    assert page['total'] == 185 and len(page['items']) == 5
    assert doc.id in [item['id'] for item in page['items']]
    for query in ('q=987654', 'numero=0987654', 'forma_pago=credito', 'q=FA01-987654', 'q=FA01-00987654'):
        response = client.get('/facturas-emitidas/page?' + query)
        assert response.status_code == 200, response.text
        assert [item['id'] for item in response.json()['items']] == [doc.id]


def test_actions_obey_features_and_suspension(db_session):
    tenant, user, doc = _make_fiscal_document(db_session, 'AC3')
    doc.estado, doc.sunat_cdr_content, doc.sunat_xml_content = 'facturada', 'cdr', 'xml'
    subscription = db_session.query(models.Subscription).filter_by(tenant_id=tenant.id).one()
    subscription.beta_feature_flags = dict(credit_notes=True, debit_notes=True, guides=True, voiding=True)
    db_session.commit()
    result = available_actions(db_session, doc, user)
    assert all(result[key] for key in ('credit_note', 'debit_note', 'create_guide', 'void', 'retry_artifacts'))
    tenant.is_active = False
    result = available_actions(db_session, doc, user)
    assert not any(result[key] for key in ('credit_note', 'debit_note', 'create_guide', 'void', 'retry_artifacts', 'retry_emission'))
