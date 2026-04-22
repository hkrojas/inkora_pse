import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { tenant as svc } from '../services/tenant';
import Spinner from '../components/ui/Spinner';
import CustomSelect from '../components/ui/CustomSelect';
import { FieldError } from '../components/ui/FieldError';
import { useToast } from '../components/ui/Toast';
import { useAuth } from '../context/AuthContext';
import {
  buildPaymentMethodErrorMap,
  digitsOnly,
  getBankAccountHint,
  normalizeWalletPhone,
  validateBankPaymentMethod,
  validateWalletPaymentMethod,
} from '../lib/utils/bankAccountValidation';
import { normalizePeruMobileInput, validatePeruMobilePhone } from '../lib/utils/peruPhoneValidation';
import {
  buildEmptyBankPaymentMethod,
  buildEmptyWalletPaymentMethod,
  normalizePaymentMethods,
  serializePaymentMethods,
} from '../lib/utils/paymentMethods';

const BANK_OPTIONS = [
  { value: 'Banco de la Nacion', label: 'Banco de la Nacion', searchText: 'banco de la nacion nacion detraccion' },
  { value: 'BCP', label: 'BCP - Banco de Credito del Peru', searchText: 'bcp banco de credito del peru credito' },
  { value: 'BBVA', label: 'BBVA', searchText: 'bbva banco continental' },
  { value: 'Interbank', label: 'Interbank', searchText: 'interbank inter bank' },
  { value: 'Scotiabank', label: 'Scotiabank', searchText: 'scotiabank scotia' },
  { value: 'BanBif', label: 'BanBif', searchText: 'banbif banca comercio' },
  { value: 'Banco Pichincha', label: 'Banco Pichincha', searchText: 'pichincha' },
  { value: 'Mibanco', label: 'Mibanco', searchText: 'mibanco mi banco' },
  { value: 'Caja Arequipa', label: 'Caja Arequipa', searchText: 'caja arequipa' },
  { value: 'Caja Huancayo', label: 'Caja Huancayo', searchText: 'caja huancayo' },
  { value: 'Caja Piura', label: 'Caja Piura', searchText: 'caja piura' },
  { value: 'Caja Cusco', label: 'Caja Cusco', searchText: 'caja cusco' },
  { value: 'Caja Sullana', label: 'Caja Sullana', searchText: 'caja sullana' },
];

const ACCOUNT_TYPE_OPTIONS = [
  { value: 'Cta Ahorro', label: 'Cta Ahorro', searchText: 'cta ahorro cuenta ahorro' },
  { value: 'Cta Corriente', label: 'Cta Corriente', searchText: 'cta corriente cuenta corriente' },
  { value: 'Cuenta Sueldo', label: 'Cuenta Sueldo', searchText: 'cuenta sueldo' },
  { value: 'Cuenta Detraccion', label: 'Cuenta Detraccion', searchText: 'cuenta detraccion detraccion' },
  { value: 'Cuenta Recaudadora', label: 'Cuenta Recaudadora', searchText: 'cuenta recaudadora' },
  { value: 'Cuenta Maestra', label: 'Cuenta Maestra', searchText: 'cuenta maestra' },
];

const BANK_CURRENCY_OPTIONS = [
  { value: 'Soles', label: 'Soles (PEN)', searchText: 'soles pen moneda peru' },
  { value: 'Dolares', label: 'Dolares (USD)', searchText: 'dolares usd dolares americanos' },
  { value: 'Euros', label: 'Euros (EUR)', searchText: 'euros eur euro' },
];

const WALLET_PROVIDER_OPTIONS = [
  { value: 'Yape', label: 'Yape', searchText: 'yape bcp billetera digital' },
  { value: 'Plin', label: 'Plin', searchText: 'plin billetera digital' },
  { value: 'Lukita', label: 'Lukita', searchText: 'lukita billetera digital' },
  { value: 'BIM', label: 'BIM', searchText: 'bim billetera digital' },
  { value: 'Agora Pay', label: 'Agora Pay', searchText: 'agora pay billetera digital' },
  { value: 'Tunki', label: 'Tunki', searchText: 'tunki billetera digital interbank' },
  { value: 'IzipayYa', label: 'IzipayYa', searchText: 'izipayya izipay ya billetera digital' },
  { value: 'Prexpe', label: 'Prexpe', searchText: 'prexpe billetera digital prex' },
  { value: 'Ligo', label: 'Ligo', searchText: 'ligo billetera digital' },
  { value: 'Yape Empresas', label: 'Yape Empresas', searchText: 'yape empresas billetera digital' },
  { value: 'Plin Empresas', label: 'Plin Empresas', searchText: 'plin empresas billetera digital' },
  { value: 'Otra billetera digital', label: 'Otra billetera digital', searchText: 'otra billetera digital personalizada' },
];

function withCurrentOption(options, currentValue) {
  const normalizedValue = String(currentValue || '').trim();
  if (!normalizedValue) return options;
  const exists = options.some((option) => String(option.value) === normalizedValue);
  if (exists) return options;
  return [
    { value: normalizedValue, label: normalizedValue, searchText: normalizedValue.toLowerCase() },
    ...options,
  ];
}

function StatusBadge({ ok, pending, labelOk, labelPending, labelNo }) {
  if (ok) return <span className="ink-aging-badge ink-aging-badge--ok">{labelOk}</span>;
  if (pending) return <span className="ink-aging-badge ink-aging-badge--warning">{labelPending || labelNo}</span>;
  return <span className="ink-aging-badge ink-aging-badge--neutral">{labelNo}</span>;
}

function ReadOnlyField({ label, value }) {
  return (
    <div className="settings-readonly-field">
      <dt className="label">{label}</dt>
      <dd className="settings-readonly-value">
        {value || <span className="settings-readonly-empty">No configurado</span>}
      </dd>
    </div>
  );
}

function PaymentMethodCard({ method, index, onChange, onRemove, errors = {} }) {
  const isWallet = method.tipo === 'wallet';
  const bankOptions = withCurrentOption(BANK_OPTIONS, method.banco);
  const accountTypeOptions = withCurrentOption(ACCOUNT_TYPE_OPTIONS, method.tipo_cuenta);
  const currencyOptions = withCurrentOption(BANK_CURRENCY_OPTIONS, method.moneda);
  const walletProviderOptions = withCurrentOption(WALLET_PROVIDER_OPTIONS, method.proveedor);
  const accountHint = getBankAccountHint(method.banco, method.tipo_cuenta);

  return (
    <div className="pdf-designer-bank-card">
      <div className="pdf-designer-bank-card-header">
        <span>{isWallet ? `Billetera digital ${index + 1}` : `Cuenta bancaria ${index + 1}`}</span>
        <button type="button" onClick={onRemove} className="pdf-designer-remove-btn">
          Eliminar
        </button>
      </div>

      <div className="pdf-designer-field-grid">
        {isWallet ? (
          <>
            <div>
              <label className="label">Billetera</label>
              <CustomSelect
                value={method.proveedor}
                onChange={(value) => onChange('proveedor', value)}
                options={walletProviderOptions}
                placeholder="Seleccionar billetera"
                searchable
                searchPlaceholder="Buscar billetera..."
                onCreateNew={(value) => onChange('proveedor', value)}
                createLabel={(value) => `+ Usar "${value}"`}
                noResultsLabel="No se encontraron billeteras"
              />
            </div>
            <div>
              <label className="label">Titular</label>
              <input
                className="input"
                value={method.titular}
                onChange={(event) => onChange('titular', event.target.value)}
                placeholder="Nombre del titular"
              />
            </div>
            <div>
              <label className="label">Numero asociado</label>
              <input
                className="input"
                value={method.numero}
                onChange={(event) => onChange('numero', normalizeWalletPhone(event.target.value))}
                placeholder="999 999 999"
                inputMode="numeric"
                style={errors.numero ? { borderColor: '#DC2626', boxShadow: 'inset 0 0 0 1px #DC2626' } : undefined}
              />
              <div className="settings-field-hint">Celular peruano: 9 digitos numericos e inicia en 9.</div>
              <FieldError message={errors.numero} />
            </div>
            <div>
              <label className="label">Nota</label>
              <input
                className="input"
                value={method.nota}
                onChange={(event) => onChange('nota', event.target.value)}
                placeholder="Opcional"
              />
            </div>
          </>
        ) : (
          <>
            <div>
              <label className="label">Banco</label>
              <CustomSelect
                value={method.banco}
                onChange={(value) => onChange('banco', value)}
                options={bankOptions}
                placeholder="Seleccionar banco"
                searchable
                searchPlaceholder="Buscar banco..."
              />
            </div>
            <div>
              <label className="label">Tipo de cuenta</label>
              <CustomSelect
                value={method.tipo_cuenta}
                onChange={(value) => onChange('tipo_cuenta', value)}
                options={accountTypeOptions}
                placeholder="Seleccionar tipo"
                searchable
                searchPlaceholder="Buscar tipo de cuenta..."
              />
            </div>
            <div>
              <label className="label">Moneda</label>
              <CustomSelect
                value={method.moneda}
                onChange={(value) => onChange('moneda', value)}
                options={currencyOptions}
                placeholder="Seleccionar moneda"
                searchable
                searchPlaceholder="Buscar moneda..."
              />
            </div>
            <div>
              <label className="label">Numero de cuenta</label>
              <input
                className="input"
                value={method.cuenta}
                onChange={(event) => onChange('cuenta', event.target.value)}
                inputMode="numeric"
                placeholder="Solo digitos"
                style={errors.cuenta ? { borderColor: '#DC2626', boxShadow: 'inset 0 0 0 1px #DC2626' } : undefined}
              />
              <div className="settings-field-hint">{accountHint}</div>
              <FieldError message={errors.cuenta} />
            </div>
            <div className="pdf-designer-field-grid-span">
              <label className="label">CCI</label>
              <input
                className="input"
                value={method.cci}
                onChange={(event) => onChange('cci', event.target.value)}
                inputMode="numeric"
                placeholder="20 digitos"
                style={errors.cci ? { borderColor: '#DC2626', boxShadow: 'inset 0 0 0 1px #DC2626' } : undefined}
              />
              <div className="settings-field-hint">CCI: 20 digitos numericos.</div>
              <FieldError message={errors.cci} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const TABS = ['empresa', 'fiscal', 'cuenta'];
const TAB_LABELS = { empresa: 'Perfil de Empresa', fiscal: 'Config. Fiscal', cuenta: 'Mi Cuenta' };

export default function ConfiguracionPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [tenantData, setTenantData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [phone, setPhone] = useState('');
  const [phoneError, setPhoneError] = useState(null);
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [paymentMethodErrors, setPaymentMethodErrors] = useState({});
  const [activeTab, setActiveTab] = useState('empresa');

  useEffect(() => {
    svc.get()
      .then((tenantResponse) => {
        setTenantData(tenantResponse);
        setPhone(normalizePeruMobileInput(tenantResponse.business_phone || ''));
        setPhoneError(null);
        setPaymentMethods(normalizePaymentMethods(tenantResponse.bank_accounts));
        setPaymentMethodErrors({});
      })
      .catch(() => toast('Error al cargar configuracion', 'error'))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nextPhoneError = validatePeruMobilePhone(phone, 'Telefono de contacto');
    const nextErrors = buildPaymentMethodErrorMap(paymentMethods);
    setPhoneError(nextPhoneError);
    setPaymentMethodErrors(nextErrors);
    if (nextPhoneError || Object.keys(nextErrors).length > 0) {
      toast('Revisa los campos de celular y los datos de cobro antes de guardar.', 'error');
      return;
    }

    setSaving(true);
    try {
      const updated = await svc.update({
        business_phone: phone,
        bank_accounts: serializePaymentMethods(paymentMethods),
      });
      setTenantData(updated);
      setPaymentMethods(normalizePaymentMethods(updated.bank_accounts));
      setPaymentMethodErrors({});
      setPhone(normalizePeruMobileInput(updated.business_phone || ''));
      setPhoneError(null);
      toast('Configuracion actualizada');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const updatePaymentMethod = (index, key, value) => {
    const nextValue = key === 'cuenta' || key === 'cci' ? digitsOnly(value) : value;

    setPaymentMethods((current) => {
      const next = current.map((method, methodIndex) => (
        methodIndex === index ? { ...method, [key]: nextValue } : method
      ));

      const nextMethodErrors = next[index]?.tipo === 'wallet'
        ? validateWalletPaymentMethod(next[index])
        : validateBankPaymentMethod(next[index]);
      setPaymentMethodErrors((currentErrors) => {
        const nextErrors = { ...currentErrors };
        if (Object.keys(nextMethodErrors).length > 0) {
          nextErrors[index] = nextMethodErrors;
        } else {
          delete nextErrors[index];
        }
        return nextErrors;
      });

      return next;
    });
  };

  const addPaymentMethod = (type) => {
    setPaymentMethods((current) => [
      ...current,
      type === 'wallet' ? buildEmptyWalletPaymentMethod() : buildEmptyBankPaymentMethod(),
    ]);
  };

  const removePaymentMethod = (index) => {
    setPaymentMethods((current) => {
      const next = current.filter((_, methodIndex) => methodIndex !== index);
      setPaymentMethodErrors(buildPaymentMethodErrorMap(next));
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const isSuperadmin = Boolean(user?.is_superadmin || user?.rol === 'superadmin');
  const isAdmin = ['admin', 'superadmin'].includes(user?.rol) || isSuperadmin;
  const companyName = tenantData?.business_name || 'Empresa no configurada';
  const companyInitial = (companyName.trim()?.charAt(0) || 'I').toUpperCase();
  const bankCount = paymentMethods.filter((method) => method.tipo !== 'wallet').length;
  const walletCount = paymentMethods.filter((method) => method.tipo === 'wallet').length;

  return (
    <div className="page-shell settings-shell">
      <div className="settings-tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="settings-tab"
            style={{
              borderBottom: activeTab === tab ? '2px solid #4F46E5' : '2px solid transparent',
              color: activeTab === tab ? '#4F46E5' : '#64748B',
            }}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {activeTab === 'empresa' && (
        <div className="settings-company-layout">
          <section className="ink-table-card settings-panel settings-company-panel">
            <div className="settings-panel-header settings-panel-header--stacked">
              <p className="page-kicker" style={{ margin: 0 }}>Identidad tributaria</p>
              <h3 className="settings-panel-title">Perfil legal y comercial</h3>
              <p className="settings-panel-copy">
                Aqui se concentra la informacion base de la empresa que se usa como referencia en documentos y operaciones internas.
              </p>
            </div>

            <div className="settings-company-identity-layout">
              <div className="settings-company-hero-card">
                <div className="settings-company-hero-mark">
                  {tenantData?.logo_filename ? (
                    <img src={tenantData.logo_filename} alt={`Logo de ${companyName}`} className="settings-company-logo" />
                  ) : (
                    <div className="settings-company-avatar">{companyInitial}</div>
                  )}
                </div>
                <div className="settings-company-hero-copy">
                  <p className="settings-company-name">{companyName}</p>
                  <p className="settings-company-meta">{tenantData?.business_ruc ? `RUC ${tenantData.business_ruc}` : 'RUC no configurado'}</p>
                </div>
              </div>

              <dl className="settings-company-readonly-grid">
                <ReadOnlyField label="Razon social" value={tenantData?.business_name} />
                <ReadOnlyField label="RUC" value={tenantData?.business_ruc} />
                <ReadOnlyField label="Direccion fiscal" value={tenantData?.business_address} />
                <ReadOnlyField label="Telefono actual" value={phone || tenantData?.business_phone} />
              </dl>
            </div>
          </section>

          <aside className="ink-table-card settings-panel settings-company-summary-panel">
            <div className="settings-panel-header settings-panel-header--stacked">
              <p className="page-kicker" style={{ margin: 0 }}>Resumen</p>
              <h3 className="settings-panel-title">Vista general</h3>
              <p className="settings-panel-copy">
                Un vistazo rapido del estado comercial y de los medios de cobro configurados.
              </p>
            </div>

            <div className="settings-company-stats">
              <div className="settings-company-stat">
                <span className="settings-company-stat-label">Telefono</span>
                <strong className="settings-company-stat-value">{phone || 'Sin telefono'}</strong>
              </div>
              <div className="settings-company-stat">
                <span className="settings-company-stat-label">Cuentas bancarias</span>
                <strong className="settings-company-stat-value">{bankCount}</strong>
              </div>
              <div className="settings-company-stat">
                <span className="settings-company-stat-label">Billeteras</span>
                <strong className="settings-company-stat-value">{walletCount}</strong>
              </div>
            </div>

            <div className="settings-company-summary-note">
              <p className="settings-company-summary-note-title">Uso en documentos</p>
              <p className="settings-company-summary-note-copy">
                Las cuentas bancarias y billeteras digitales configuradas aqui se imprimen en el pie del PDF bajo "Datos para la Transferencia".
              </p>
            </div>
          </aside>

          {isAdmin && (
            <section className="ink-table-card settings-panel settings-company-form-panel">
              <form onSubmit={handleSubmit} className="settings-company-form">
                <div className="settings-company-form-top">
                  <div className="settings-company-contact-card">
                    <div className="pdf-designer-section-head">
                      <h3>Contacto comercial</h3>
                      <p>Actualiza el telefono visible para el equipo y para las referencias operativas de la empresa.</p>
                    </div>

                    <div className="settings-company-contact-grid">
                      <div>
                        <label className="label">Telefono de contacto</label>
                        <input
                          className="input"
                          value={phone}
                          onChange={(event) => {
                            const nextPhone = normalizePeruMobileInput(event.target.value);
                            setPhone(nextPhone);
                            setPhoneError(validatePeruMobilePhone(nextPhone, 'Telefono de contacto'));
                          }}
                          placeholder="+51 999 999 999"
                          inputMode="numeric"
                          style={phoneError ? { borderColor: '#DC2626', boxShadow: 'inset 0 0 0 1px #DC2626' } : undefined}
                        />
                        <div className="settings-field-hint">Celular peruano: 9 digitos numericos e inicia en 9.</div>
                        <FieldError message={phoneError} />
                      </div>
                    </div>
                  </div>

                  <div className="settings-company-help-card">
                    <p className="page-kicker" style={{ margin: 0 }}>Impacto</p>
                    <p className="settings-company-help-title">Lo que estas configurando aqui</p>
                    <p className="settings-company-help-copy">
                      Este perfil alimenta la identidad comercial del tenant. Los medios de cobro tambien se reutilizan en la plantilla PDF sin volver a cargarlos en cada cotizacion.
                    </p>
                  </div>
                </div>

                <div className="settings-company-transfer-section">
                  <div className="pdf-designer-section-head">
                    <h3>Datos para la transferencia</h3>
                    <p>
                      Administra cuentas bancarias y billeteras digitales desde un solo lugar para que el pie del PDF siempre salga consistente.
                    </p>
                  </div>

                  <div className="settings-payment-toolbar">
                    <button type="button" onClick={() => addPaymentMethod('bank')} className="btn-secondary">
                      + Agregar cuenta bancaria
                    </button>
                    <button type="button" onClick={() => addPaymentMethod('wallet')} className="btn-secondary">
                      + Agregar billetera digital
                    </button>
                  </div>

                  {paymentMethods.length > 0 ? (
                    <div className="pdf-designer-bank-list settings-payment-list">
                      {paymentMethods.map((method, index) => (
                        <PaymentMethodCard
                          key={`${method.tipo}-${index}`}
                          method={method}
                          index={index}
                          errors={paymentMethodErrors[index]}
                          onChange={(key, value) => updatePaymentMethod(index, key, value)}
                          onRemove={() => removePaymentMethod(index)}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="settings-empty-card">
                      Todavia no hay cuentas bancarias ni billeteras digitales configuradas.
                    </div>
                  )}
                </div>

                <div className="settings-form-actions settings-form-actions--company">
                  <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
                    {saving && <Spinner size="sm" />} Guardar cambios
                  </button>
                </div>
              </form>
            </section>
          )}
        </div>
      )}

      {activeTab === 'fiscal' && (
        <div className="ink-table-card settings-panel">
          <div className="settings-panel-header">
            <p className="page-kicker" style={{ margin: 0 }}>Credenciales y Certificados</p>
          </div>

          <dl className="settings-status-list">
            <div className="settings-status-row">
              <div>
                <p style={{ fontSize: '14px', fontWeight: 600, color: '#0F172A' }}>Token ApisPeru</p>
                <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>Conexion API para consulta RUC/DNI.</p>
              </div>
              <StatusBadge
                ok={tenantData?.has_apisperu_token}
                labelOk="Configurado"
                labelNo="No configurado"
              />
            </div>

            <div className="settings-status-row">
              <div>
                <p style={{ fontSize: '14px', fontWeight: 600, color: '#0F172A' }}>Credenciales SOL</p>
                <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>Transmision a SUNAT.</p>
              </div>
              <StatusBadge
                ok={tenantData?.has_sunat_credentials}
                pending={!tenantData?.has_sunat_credentials}
                labelOk="Configuradas"
                labelPending="Pendiente"
                labelNo="Pendiente"
              />
            </div>

            <div className="settings-status-row">
              <div>
                <p style={{ fontSize: '14px', fontWeight: 600, color: '#0F172A' }}>Certificado digital (PFX)</p>
                <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>Firma electronica de XML.</p>
              </div>
              <StatusBadge
                ok={tenantData?.has_sunat_cert}
                labelOk="Cargado"
                labelNo="No cargado"
              />
            </div>
          </dl>

          <div className="settings-restricted-alert">
            <span style={{ fontSize: '18px', color: '#818CF8', marginTop: '1px' }}>ℹ</span>
            <div>
              <p style={{ color: '#fff', fontWeight: 700, fontSize: '14px', marginBottom: '4px' }}>Actualizacion Restringida</p>
              <p style={{ color: '#C7D2FE', fontSize: '12px' }}>
                {isSuperadmin ? (
                  <>
                    Como superadmin, gestiona credenciales fiscales desde{' '}
                    <Link to="/superadmin" style={{ color: '#A5B4FC', textDecoration: 'underline' }}>
                      Superadmin
                    </Link>
                    .
                  </>
                ) : (
                  'Contacte al administrador de la plataforma para escalar permisos.'
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'cuenta' && (
        <div className="ink-table-card settings-panel">
          <div className="settings-panel-header">
            <p className="page-kicker" style={{ margin: 0 }}>Datos de Sesion</p>
          </div>

          <div className="settings-account-hero">
            <div className="settings-account-avatar">
              {((user?.nombre_completo || user?.email || 'U')[0]).toUpperCase()}
            </div>
            <div>
              <p style={{ fontSize: '18px', fontWeight: 700, color: '#0F172A' }}>{user?.nombre_completo || user?.email}</p>
              <p style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.1em', marginTop: '4px' }}>
                {isSuperadmin ? 'superadmin' : user?.rol}
              </p>
            </div>
          </div>

          <dl className="grid gap-4 md:grid-cols-3">
            <div>
              <dt className="label">Nombre</dt>
              <dd style={{ fontSize: '14px', color: 'var(--text-primary)', padding: '8px 0' }}>{user?.nombre_completo || '--'}</dd>
            </div>
            <div>
              <dt className="label">Email</dt>
              <dd style={{ fontSize: '14px', color: 'var(--text-primary)', padding: '8px 0' }}>{user?.email}</dd>
            </div>
            <div>
              <dt className="label">Rol</dt>
              <dd style={{ fontSize: '14px', color: 'var(--text-primary)', padding: '8px 0' }}>
                {isSuperadmin ? 'superadmin' : user?.rol}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}
