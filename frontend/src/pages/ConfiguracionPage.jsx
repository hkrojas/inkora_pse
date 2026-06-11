import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { tenant as svc } from '../services/tenant';
import { Sun, Moon, Monitor, Building2, ShieldCheck, User, Palette, CreditCard, AlertTriangle, Eye, EyeOff, KeyRound, Phone, Landmark, Smartphone, WalletCards, LockKeyhole, FileCheck2, BadgeCheck, FileKey2, RadioTower, ImageUp, QrCode, MessageCircle, Mail } from 'lucide-react';
import Spinner from '../components/ui/Spinner';
import CustomSelect from '../components/ui/CustomSelect';
import FormField from '../components/ui/FormField';
import PaymentQrCropper from '../components/settings/PaymentQrCropper';
import { useToast } from '../components/ui/Toast';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { api } from '../lib/utils/api';
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
import {
  DEFAULT_SHARE_TEMPLATES,
  SHARE_TEMPLATE_PLACEHOLDERS,
  extractCommunicationTemplates,
  mergeCommunicationTemplates,
} from '../lib/utils/communicationTemplates';

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
  if (ok) return <span className="status-pill ok">{labelOk}</span>;
  if (pending) return <span className="status-pill warn">{labelPending || labelNo}</span>;
  return <span className="status-pill err">{labelNo}</span>;
}

function FiscalStatusTile({ icon: Icon, tone, label, value, children }) {
  return (
    <div className={`status-tile fiscal-status-tile is-${tone}`}>
      <div className="fiscal-status-icon">
        <Icon size={18} />
      </div>
      <div>
        <div className="tile-label">{label}</div>
        <div className="tile-value">{value}</div>
      </div>
      <div className="fiscal-status-line">
        {children}
      </div>
    </div>
  );
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

const BUSINESS_NAME_MAX_LENGTH = 180;
const BUSINESS_ADDRESS_MAX_LENGTH = 250;
const TENANT_ASSET_MAX_SIZE_MB = 25;
const LOGO_MAX_SIZE_BYTES = TENANT_ASSET_MAX_SIZE_MB * 1024 * 1024;
const LOGO_ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp'];

function normalizeBusinessText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function validateBusinessName(value) {
  const normalized = normalizeBusinessText(value);
  if (!normalized) return 'La razon social es obligatoria.';
  if (normalized.length < 2) return 'La razon social debe tener al menos 2 caracteres.';
  if (normalized.length > BUSINESS_NAME_MAX_LENGTH) {
    return `La razon social no debe superar ${BUSINESS_NAME_MAX_LENGTH} caracteres.`;
  }
  return null;
}

function validateBusinessAddress(value) {
  const normalized = normalizeBusinessText(value);
  if (!normalized) return 'El domicilio fiscal es obligatorio.';
  if (normalized.length < 5) return 'El domicilio fiscal debe tener al menos 5 caracteres.';
  if (normalized.length > BUSINESS_ADDRESS_MAX_LENGTH) {
    return `El domicilio fiscal no debe superar ${BUSINESS_ADDRESS_MAX_LENGTH} caracteres.`;
  }
  return null;
}

function PaymentMethodCard({ method, index, onChange, onRemove, errors = {} }) {
  const isWallet = method.tipo === 'wallet';
  const bankOptions = withCurrentOption(BANK_OPTIONS, method.banco);
  const accountTypeOptions = withCurrentOption(ACCOUNT_TYPE_OPTIONS, method.tipo_cuenta);
  const currencyOptions = withCurrentOption(BANK_CURRENCY_OPTIONS, method.moneda);
  const walletProviderOptions = withCurrentOption(WALLET_PROVIDER_OPTIONS, method.proveedor);
  const accountHint = getBankAccountHint(method.banco, method.tipo_cuenta);

  return (
    <div className="settings-bank-card">
      <div className="settings-bank-card-header">
        <span>{isWallet ? `Billetera digital ${index + 1}` : `Cuenta bancaria ${index + 1}`}</span>
        <button type="button" onClick={onRemove} className="settings-remove-btn">
          Eliminar
        </button>
      </div>

      <div className="settings-field-grid">
        {isWallet ? (
          <>
            <FormField label="Billetera" icon={WalletCards}>
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
            </FormField>
            <FormField label="Titular" icon={User}>
              <input
                className="input"
                value={method.titular}
                onChange={(event) => onChange('titular', event.target.value)}
                placeholder="Nombre del titular"
              />
            </FormField>
            <FormField
              label="Numero asociado"
              icon={Smartphone}
              hint="Celular peruano: 9 dígitos numéricos e inicia en 9."
              error={errors.numero}
            >
              <input
                className={`input${errors.numero ? ' input-error' : ''}`}
                value={method.numero}
                onChange={(event) => onChange('numero', normalizeWalletPhone(event.target.value))}
                placeholder="999 999 999"
                inputMode="numeric"
              />
            </FormField>
            <FormField label="Nota">
              <input
                className="input"
                value={method.nota}
                onChange={(event) => onChange('nota', event.target.value)}
                placeholder="Opcional"
              />
            </FormField>
          </>
        ) : (
          <>
            <FormField label="Banco" icon={Landmark}>
              <CustomSelect
                value={method.banco}
                onChange={(value) => onChange('banco', value)}
                options={bankOptions}
                placeholder="Seleccionar banco"
                searchable
                searchPlaceholder="Buscar banco..."
              />
            </FormField>
            <FormField label="Tipo de cuenta" icon={CreditCard}>
              <CustomSelect
                value={method.tipo_cuenta}
                onChange={(value) => onChange('tipo_cuenta', value)}
                options={accountTypeOptions}
                placeholder="Seleccionar tipo"
                searchable
                searchPlaceholder="Buscar tipo de cuenta..."
              />
            </FormField>
            <FormField label="Moneda">
              <CustomSelect
                value={method.moneda}
                onChange={(value) => onChange('moneda', value)}
                options={currencyOptions}
                placeholder="Seleccionar moneda"
                searchable
                searchPlaceholder="Buscar moneda..."
              />
            </FormField>
            <FormField label="Numero de cuenta" hint={accountHint} error={errors.cuenta}>
              <input
                className={`input${errors.cuenta ? ' input-error' : ''}`}
                value={method.cuenta}
                onChange={(event) => onChange('cuenta', event.target.value)}
                inputMode="numeric"
                placeholder="Solo dígitos"
              />
            </FormField>
            <FormField
              label="CCI"
              hint="CCI: 20 dígitos numéricos."
              error={errors.cci}
              className="settings-field-grid-span"
            >
              <input
                className={`input${errors.cci ? ' input-error' : ''}`}
                value={method.cci}
                onChange={(event) => onChange('cci', event.target.value)}
                inputMode="numeric"
                placeholder="20 dígitos"
              />
            </FormField>
          </>
        )}
      </div>
    </div>
  );
}

const TABS = ['empresa', 'fiscal', 'cuenta', 'seguridad', 'apariencia'];
const TAB_LABELS = { empresa: 'Perfil de Empresa', fiscal: 'Config. Fiscal', cuenta: 'Mi Cuenta', seguridad: 'Seguridad', apariencia: 'Apariencia' };
const TAB_DESCRIPTIONS = {
  empresa: 'Identidad y cobros',
  fiscal: 'SUNAT y certificados',
  cuenta: 'Usuario actual',
  seguridad: 'Acceso seguro',
  apariencia: 'Tema y PDFs',
};

const TAB_ICONS = { empresa: Building2, fiscal: ShieldCheck, cuenta: User, seguridad: KeyRound, apariencia: Palette };
const DEFAULT_PDF_PRIMARY_COLOR = '#004AAD';
const DEFAULT_PDF_NOTE_COLOR = '#FF0000';
const HEX_COLOR_PATTERN = /^#[0-9A-Fa-f]{6}$/;

function getSafePdfColor(value, fallback) {
  const normalized = String(value || '').trim();
  return HEX_COLOR_PATTERN.test(normalized) ? normalized.toUpperCase() : fallback;
}

function AparienciaPanel({ tenantData }) {
  const { theme, setTheme, resolvedTheme, noise, setNoise } = useTheme();
  const documentPrimaryColor = getSafePdfColor(tenantData?.primary_color, DEFAULT_PDF_PRIMARY_COLOR);
  const documentNoteColor = getSafePdfColor(tenantData?.pdf_note_1_color, DEFAULT_PDF_NOTE_COLOR);

  const themeOptions = [
    { value: 'light', label: 'Claro', Icon: Sun },
    { value: 'dark', label: 'Oscuro', Icon: Moon },
    { value: 'system', label: 'Sistema', Icon: Monitor },
  ];

  return (
    <div className="settings-view">
      <div className="appearance-card settings-panel settings-appearance-panel">
        <div className="settings-section-title settings-section-title--stacked">
          <div className="settings-icon-box">
            <Palette size={15} />
          </div>
          <div>
            <h3>Tema visual</h3>
            <p>Personaliza el tema de Inkora. Los cambios se aplican de inmediato.</p>
          </div>
        </div>
        <div className="theme-options">
          {themeOptions.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={(event) => setTheme(opt.value, event)}
              className={`theme-btn${theme === opt.value ? ' active' : ''}`}
            >
              <div className={`preview-mock theme-preview theme-preview--${opt.value}${opt.value === 'dark' ? ' dark-mock' : ''}`}>
                <opt.Icon size={18} strokeWidth={1.5} />
                <span />
              </div>
              {opt.label}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-[var(--color-text-soft)] mt-3">
          Tema activo: <strong className="text-[var(--color-text)]">{resolvedTheme === 'dark' ? 'Oscuro' : 'Claro'}</strong>
          {theme === 'system' && ' (heredado del sistema)'}
        </p>
      </div>

      <div className="appearance-card settings-panel settings-texture-panel">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-1">Textura editorial</p>
            <p className="text-[14px] font-semibold text-[var(--color-text)]">Grain de papel</p>
            <p className="text-[12px] text-[var(--color-text-muted)] mt-1">
              Agrega una textura sutil tipo prensa al fondo. Solo afecta visualmente.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setNoise(!noise)}
            className={`settings-toggle${noise ? ' active' : ''}`}
            aria-label={noise ? 'Desactivar grain' : 'Activar grain'}
          >
            <span className="settings-toggle-knob" />
          </button>
        </div>
        <div className={`preview-mock settings-texture-preview mt-4${resolvedTheme === 'dark' ? ' dark-mock' : ''}${noise ? ' is-active' : ''}`}>
          {noise ? 'Grain activado' : 'Sin grain'}
        </div>
      </div>

      <div
        className="appearance-card settings-panel settings-pdf-colors-panel"
        style={{
          '--settings-pdf-primary': documentPrimaryColor,
          '--settings-pdf-note': documentNoteColor,
        }}
      >
        <div className="settings-pdf-colors-copy">
          <div className="settings-section-title settings-section-title--stacked">
            <div className="settings-icon-box">
              <FileCheck2 size={15} />
            </div>
            <div>
              <h3>Colores de documentos PDF</h3>
              <p>Personaliza la plantilla usada en cotizaciones, facturas, boletas, guias y documentos comerciales.</p>
            </div>
          </div>

          <div className="settings-pdf-color-swatches">
            <div>
              <span style={{ background: documentPrimaryColor }} />
              <small>Principal</small>
              <strong>{documentPrimaryColor}</strong>
            </div>
            <div>
              <span style={{ background: documentNoteColor }} />
              <small>Nota</small>
              <strong>{documentNoteColor}</strong>
            </div>
          </div>

          <Link to="/diseno-pdf" className="btn-primary settings-pdf-colors-link">
            <Palette size={15} /> Editar colores PDF
          </Link>
        </div>

        <div className="settings-pdf-mini-preview" aria-hidden="true">
          <div className="settings-pdf-mini-head">
            <div />
            <span>COTIZACION</span>
          </div>
          <div className="settings-pdf-mini-line" />
          <div className="settings-pdf-mini-table">
            <span>N</span>
            <span>DESCRIPCION</span>
            <span>TOTAL</span>
          </div>
          <div className="settings-pdf-mini-row">
            <span />
            <span />
            <span />
          </div>
          <div className="settings-pdf-mini-total">
            <span>IMPORTE TOTAL</span>
            <strong>S/ 0.00</strong>
          </div>
          <div className="settings-pdf-mini-note">Nota destacada del documento</div>
        </div>
      </div>
    </div>
  );
}

function PasswordInput({ label, value, onChange, required }) {
  const [show, setShow] = useState(false);
  return (
    <FormField label={label} icon={LockKeyhole} required={required} className="settings-password-field">
      <div className="settings-password-control">
        <input
          type={show ? 'text' : 'password'}
          className="input"
          value={value}
          onChange={onChange}
          required={required}
          minLength={10}
        />
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          tabIndex={-1}
          className="settings-password-toggle"
          aria-label={show ? 'Ocultar contraseña' : 'Mostrar contraseña'}
        >
          {show ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      </div>
    </FormField>
  );
}

function SeguridadPanel() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const setField = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (form.new_password !== form.confirm_password) {
      setError('Las contraseñas nuevas no coinciden.');
      return;
    }
    if (form.new_password.length < 10) {
      setError('La contraseña debe tener al menos 10 caracteres.');
      return;
    }
    setSaving(true);
    try {
      const data = await api.post('/users/me/change-password', {
        current_password: form.current_password,
        new_password: form.new_password,
        confirm_password: form.confirm_password,
      });
      if (data.access_token) {
        const storage = localStorage.getItem('token') ? localStorage : sessionStorage;
        localStorage.removeItem('token');
        sessionStorage.removeItem('token');
        storage.setItem('token', data.access_token);
      }
      await refreshUser();
      setForm({ current_password: '', new_password: '', confirm_password: '' });
      toast('Contraseña actualizada correctamente', 'success');
      if (user?.must_change_password) {
        setTimeout(() => navigate('/dashboard', { replace: true }), 800);
      }
    } catch (err) {
      setError(err.message || 'No se pudo cambiar la contraseña. Revisa tu conexión e inténtalo nuevamente.');
    } finally {
      setSaving(false);
    }
  };

  const isFirstLogin = Boolean(user?.must_change_password);

  return (
    <div className="settings-view">
      {isFirstLogin && (
        <div className="proto-alert warning">
          <ShieldCheck size={15} className="flex-shrink-0 mt-0.5" />
          <div>
            <p className="settings-alert-title">Debes cambiar tu contraseña antes de continuar</p>
            <p className="settings-alert-copy">
              Es la primera vez que accedes con esta cuenta. Elige una contraseña segura que solo tú conozcas.
            </p>
          </div>
        </div>
      )}

      <div className="settings-rail-card settings-panel settings-security-panel">
        <div className="settings-rail-card-header">
          <div className="settings-section-title">
            <div className="settings-icon-box">
              <KeyRound size={15} />
            </div>
            <div>
              <h3>Cambiar contraseña</h3>
              <p>Actualiza tu contraseña de acceso periódicamente para mantener tu cuenta protegida.</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="settings-form-body">
          <div className="settings-security-grid">
            <div className="settings-security-fields">
              <PasswordInput
                label={isFirstLogin ? 'Contraseña temporal (la que te enviaron)' : 'Contraseña actual'}
                value={form.current_password}
                onChange={setField('current_password')}
                required
              />
              <PasswordInput
                label="Nueva contraseña"
                value={form.new_password}
                onChange={setField('new_password')}
                required
              />
              <PasswordInput
                label="Confirmar nueva contraseña"
                value={form.confirm_password}
                onChange={setField('confirm_password')}
                required
              />
            </div>

            <aside className="settings-password-rules">
              <span className="settings-fiscal-kicker">Política de seguridad</span>
              <strong>Contraseña robusta</strong>
              <p>Usa una clave única para Inkora. El cambio invalida sesiones antiguas si el backend detecta credenciales previas.</p>
              <ul>
                <li>Minimo 10 caracteres</li>
                <li>Al menos una letra</li>
                <li>Al menos un numero</li>
              </ul>
            </aside>
          </div>

          {error && (
            <div className="proto-alert danger">
              <p className="settings-alert-copy">{error}</p>
            </div>
          )}

          <div className="settings-form-actions">
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? 'Guardando...' : 'Cambiar contraseña'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function ConfiguracionPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const logoInputRef = useRef(null);
  const paymentQrInputRef = useRef(null);
  const initialTab = searchParams.get('tab') || 'empresa';
  const [tenantData, setTenantData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingPaymentQr, setUploadingPaymentQr] = useState(false);
  const [logoError, setLogoError] = useState(null);
  const [paymentQrError, setPaymentQrError] = useState(null);
  const [paymentQrCropFile, setPaymentQrCropFile] = useState(null);
  const [businessName, setBusinessName] = useState('');
  const [businessAddress, setBusinessAddress] = useState('');
  const [businessErrors, setBusinessErrors] = useState({});
  const [phone, setPhone] = useState('');
  const [phoneError, setPhoneError] = useState(null);
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [paymentMethodErrors, setPaymentMethodErrors] = useState({});
  const [communicationTemplates, setCommunicationTemplates] = useState(() => extractCommunicationTemplates([]));
  const [activeTab, setActiveTab] = useState(TABS.includes(initialTab) ? initialTab : 'empresa');
  const [tabDirection, setTabDirection] = useState('forward');

  useEffect(() => {
    const controller = new AbortController();
    svc.get({ signal: controller.signal })
      .then((tenantResponse) => {
        setTenantData(tenantResponse);
        setBusinessName(tenantResponse.business_name || '');
        setBusinessAddress(tenantResponse.business_address || '');
        setBusinessErrors({});
        setPhone(normalizePeruMobileInput(tenantResponse.business_phone || ''));
        setPhoneError(null);
        setPaymentMethods(normalizePaymentMethods(tenantResponse.bank_accounts));
        setCommunicationTemplates(extractCommunicationTemplates(tenantResponse.bank_accounts));
        setPaymentMethodErrors({});
      })
      .catch((err) => {
        if (err?.isCanceled) return;
        toast('No se pudo cargar la configuración. Revisa tu conexión e inténtalo nuevamente.', 'error');
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nextBusinessName = normalizeBusinessText(businessName);
    const nextBusinessAddress = normalizeBusinessText(businessAddress);
    const nextBusinessErrors = {
      business_name: validateBusinessName(nextBusinessName),
      business_address: validateBusinessAddress(nextBusinessAddress),
    };
    const nextPhoneError = validatePeruMobilePhone(phone, 'Teléfono de contacto');
    const nextErrors = buildPaymentMethodErrorMap(paymentMethods);
    setBusinessErrors(nextBusinessErrors);
    setPhoneError(nextPhoneError);
    setPaymentMethodErrors(nextErrors);
    if (
      Object.values(nextBusinessErrors).some(Boolean)
      || nextPhoneError
      || Object.keys(nextErrors).length > 0
    ) {
      toast('Revisa los datos fiscales, celular y medios de cobro antes de guardar.', 'error');
      return;
    }

    setSaving(true);
    try {
      const updated = await svc.update({
        business_name: nextBusinessName,
        business_address: nextBusinessAddress,
        business_phone: phone,
        bank_accounts: mergeCommunicationTemplates(
          serializePaymentMethods(paymentMethods),
          communicationTemplates,
        ),
      });
      setTenantData(updated);
      setBusinessName(updated.business_name || '');
      setBusinessAddress(updated.business_address || '');
      setBusinessErrors({});
      setPaymentMethods(normalizePaymentMethods(updated.bank_accounts));
      setCommunicationTemplates(extractCommunicationTemplates(updated.bank_accounts));
      setPaymentMethodErrors({});
      setPhone(normalizePeruMobileInput(updated.business_phone || ''));
      setPhoneError(null);
      toast('Configuración actualizada');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleLogoChange = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    if (!LOGO_ALLOWED_TYPES.includes(file.type)) {
      setLogoError('Formato no permitido. Usa PNG, JPG, JPEG o WEBP.');
      toast('Formato de logo no permitido.', 'error');
      return;
    }

    if (file.size > LOGO_MAX_SIZE_BYTES) {
      setLogoError(`El logo no debe superar ${TENANT_ASSET_MAX_SIZE_MB} MB.`);
      toast('El logo excede el tamano maximo permitido.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    setLogoError(null);
    setUploadingLogo(true);
    try {
      const response = await svc.uploadLogo(formData);
      setTenantData((current) => ({
        ...(current || {}),
        logo_filename: response.url,
      }));
      toast('Logo actualizado');
    } catch (err) {
      setLogoError(err.message || 'No se pudo subir el logo.');
      toast(err.message || 'No se pudo subir el logo.', 'error');
    } finally {
      setUploadingLogo(false);
    }
  };

  const uploadPaymentQrFile = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    setPaymentQrError(null);
    setUploadingPaymentQr(true);
    try {
      const response = await svc.uploadPaymentQr(formData);
      setTenantData((current) => ({
        ...(current || {}),
        payment_qr_filename: response.url,
      }));
      toast('QR de cobro actualizado');
    } catch (err) {
      const message = err.message || 'No se pudo subir el QR de cobro.';
      setPaymentQrError(message);
      toast(message, 'error');
      throw err;
    } finally {
      setUploadingPaymentQr(false);
    }
  };

  const handlePaymentQrChange = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    if (!LOGO_ALLOWED_TYPES.includes(file.type)) {
      setPaymentQrError('Formato no permitido. Usa PNG, JPG, JPEG o WEBP.');
      toast('Formato de QR no permitido.', 'error');
      return;
    }

    if (file.size > LOGO_MAX_SIZE_BYTES) {
      setPaymentQrError(`El QR no debe superar ${TENANT_ASSET_MAX_SIZE_MB} MB.`);
      toast('El QR excede el tamano maximo permitido.', 'error');
      return;
    }

    setPaymentQrError(null);
    setPaymentQrCropFile(file);
  };

  const handlePaymentQrCropConfirm = async (croppedFile) => {
    try {
      await uploadPaymentQrFile(croppedFile);
      setPaymentQrCropFile(null);
    } catch {
      // uploadPaymentQrFile already shows the user-facing error.
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

  const setCommunicationTemplateField = (key) => (event) => {
    setCommunicationTemplates((current) => ({
      ...current,
      [key]: event.target.value,
    }));
  };

  const resetCommunicationTemplates = () => {
    setCommunicationTemplates(extractCommunicationTemplates([
      {
        tipo: 'communication_templates',
        ...DEFAULT_SHARE_TEMPLATES,
      },
    ]));
  };

  const handleTabChange = (nextTab) => {
    if (nextTab === activeTab) return;
    const currentIndex = TABS.indexOf(activeTab);
    const nextIndex = TABS.indexOf(nextTab);
    setTabDirection(nextIndex > currentIndex ? 'forward' : 'backward');
    setActiveTab(nextTab);
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const isSuperadmin = Boolean(user?.is_superadmin);
  const isAdmin = user?.rol === 'admin' || isSuperadmin;
  const companyFormId = 'settings-company-form';
  const companyName = tenantData?.business_name || 'Empresa no configurada';
  const companyInitial = (companyName.trim()?.charAt(0) || 'I').toUpperCase();
  const bankCount = paymentMethods.filter((method) => method.tipo !== 'wallet').length;
  const walletCount = paymentMethods.filter((method) => method.tipo === 'wallet').length;
  const fiscalReady = Boolean(tenantData?.has_sunat_credentials && tenantData?.has_sunat_cert);
  const hasSmartPseCpeCredentials = Boolean(tenantData?.has_smartpse_credentials);
  const collectionsReady = Boolean(phone && paymentMethods.length > 0);
  const setupStatus = fiscalReady && collectionsReady ? 'Lista para operar' : 'Requiere revision';
  const fiscalConfiguredCount = [
    hasSmartPseCpeCredentials,
    tenantData?.has_sunat_credentials,
    tenantData?.has_sunat_cert,
    true,
  ].filter(Boolean).length;

  return (
    <div className="page-shell configuracion-page">
      <div className="page-head ink-enter-1">
        <div>
          <p className="eyebrow">Panel de control</p>
          <h2>Configuración</h2>
          <p>
            Identidad, emisión fiscal, cuenta y apariencia desde un solo lugar
          </p>
        </div>
      </div>

      <section className="settings-command-card ink-enter-2">
        <div className="settings-command-main">
          <div className="settings-command-kicker">
            <Building2 size={14} />
            Configuración operativa
          </div>
          <div className="settings-command-identity">
            {tenantData?.logo_filename ? (
              <img src={tenantData.logo_filename} alt={`Logo ${companyName}`} className="settings-command-logo" />
            ) : (
              <div className="settings-command-avatar">{companyInitial}</div>
            )}
            <div>
              <h3>{companyName}</h3>
              <p>{tenantData?.business_ruc ? `RUC ${tenantData.business_ruc}` : 'RUC no configurado'}</p>
            </div>
          </div>
          <p className="settings-command-copy">
            Revisa los datos que impactan directamente en cotizaciones, comprobantes, guias y PDF comerciales.
          </p>
          <div className="settings-command-actions">
            <span className={`status-pill ${fiscalReady ? 'ok' : 'warn'}`}>{setupStatus}</span>
            {isAdmin && activeTab === 'empresa' && (
              <button
                type="button"
                onClick={() => document.getElementById(companyFormId)?.requestSubmit()}
                disabled={saving}
                className="document-list-hero-btn document-list-hero-btn--primary"
              >
                {saving && <Spinner size="sm" />} Guardar cambios
              </button>
            )}
          </div>
        </div>

        <div className="settings-command-metrics">
          <article>
            <span>Empresa</span>
            <strong>1 perfil</strong>
            <small>Identidad comercial activa</small>
          </article>
          <article>
            <span>SUNAT</span>
            <strong>{tenantData?.has_sunat_credentials ? 'Lista' : 'Parcial'}</strong>
            <small>{tenantData?.has_sunat_credentials ? 'Credenciales activas' : 'Configuración pendiente'}</small>
          </article>
          <article>
            <span>Cobros</span>
            <strong>{bankCount + walletCount}</strong>
            <small>{collectionsReady ? 'Medios visibles en PDF' : 'Falta contacto o cobro'}</small>
          </article>
          <article>
            <span>Cuenta</span>
            <strong>{isSuperadmin ? 'SA' : user?.rol || 'Usuario'}</strong>
            <small>Sesión con permisos operativos</small>
          </article>
        </div>
      </section>

      <div className="settings-tabs-bar ink-enter-3">
        {TABS.map((tab) => {
          const Icon = TAB_ICONS[tab];
          return (
            <button
              key={tab}
              type="button"
              onClick={() => handleTabChange(tab)}
              className={`settings-tab-btn${activeTab === tab ? ' active' : ''}`}
            >
              <span className="settings-tab-icon">
                <Icon size={15} />
              </span>
              <span>
                <strong>{TAB_LABELS[tab]}</strong>
                <small>{TAB_DESCRIPTIONS[tab]}</small>
              </span>
            </button>
          );
        })}
      </div>

      {activeTab === 'empresa' && (
        <div className={`settings-view settings-tab-panel settings-tab-panel--${tabDirection}`}>
          <div className="settings-hero-card settings-panel">
            <div className="settings-hero-grid">
              <div>
                <div className="flex items-center gap-3 mb-4">
                  {tenantData?.logo_filename ? (
                    <img src={tenantData.logo_filename} alt={`Logo ${companyName}`} className="h-10 w-10 rounded-xl object-cover" />
                  ) : (
                    <div className="account-avatar text-sm">{companyInitial}</div>
                  )}
                  <div>
                    <p className="text-[15px] font-extrabold text-[var(--color-text)]">{companyName}</p>
                    <p className="text-[11px] text-[var(--color-text-muted)]">{tenantData?.business_ruc ? `RUC ${tenantData.business_ruc}` : 'RUC no configurado'}</p>
                  </div>
                </div>
                <dl className="space-y-2">
                  <ReadOnlyField label="Razón social" value={tenantData?.business_name} />
                  <ReadOnlyField label="Dirección fiscal" value={tenantData?.business_address} />
                  <ReadOnlyField label="Teléfono" value={phone || tenantData?.business_phone} />
                </dl>
              </div>
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">Medios de cobro</p>
                <div className="credential-list settings-company-summary">
                  <div className="credential-item">
                    <span className="ci-label">Cuentas bancarias</span>
                    <span className="ci-value font-bold text-[var(--color-text)]">{bankCount}</span>
                  </div>
                  <div className="credential-item">
                    <span className="ci-label">Billeteras digitales</span>
                    <span className="ci-value font-bold text-[var(--color-text)]">{walletCount}</span>
                  </div>
                </div>
                <div className="hint-card mt-3">
                  <CreditCard size={13} className="flex-shrink-0 mt-0.5" />
                  <span>Los datos de cobro se imprimen en el pie del PDF automaticamente.</span>
                </div>
              </div>
            </div>
          </div>

          {isAdmin && (
            <div className="settings-rail-card settings-panel settings-collections-panel">
              <div className="settings-rail-card-header">
                <div className="settings-section-title">
                  <div className="settings-icon-box">
                    <CreditCard size={15} />
                  </div>
                  <div>
                    <h3>Datos SUNAT, contacto y medios de cobro</h3>
                    <p>Razón social y domicilio fiscal deben coincidir con la ficha RUC vigente.</p>
                  </div>
                </div>
                <div className="settings-section-badges">
                  <span>SUNAT</span>
                  <span>PDF comercial</span>
                  <span>Cobranza</span>
                </div>
              </div>
              <form id={companyFormId} onSubmit={handleSubmit} className="settings-company-edit-form">
                <div className="settings-logo-upload-card">
                  <div className="settings-logo-upload-preview">
                    {tenantData?.logo_filename ? (
                      <img src={tenantData.logo_filename} alt={`Logo ${companyName}`} />
                    ) : (
                      <span>{companyInitial}</span>
                    )}
                  </div>
                  <div className="settings-logo-upload-copy">
                    <p>Logo de empresa</p>
                    <span>Se usa en cotizaciones, comprobantes, guias y PDFs comerciales. PNG, JPG o WEBP hasta {TENANT_ASSET_MAX_SIZE_MB} MB.</span>
                    {logoError && <strong>{logoError}</strong>}
                  </div>
                  <div className="settings-logo-upload-actions">
                    <input
                      ref={logoInputRef}
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      onChange={handleLogoChange}
                      className="sr-only"
                    />
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => logoInputRef.current?.click()}
                      disabled={uploadingLogo}
                    >
                      {uploadingLogo ? (
                        <>
                          <Spinner size="sm" /> Subiendo...
                        </>
                      ) : (
                        <>
                          <ImageUp size={15} /> Subir logo
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <div className="settings-logo-upload-card settings-payment-qr-card">
                  <div className="settings-logo-upload-preview settings-payment-qr-preview">
                    {tenantData?.payment_qr_filename ? (
                      <img src={tenantData.payment_qr_filename} alt={`QR de cobro ${companyName}`} />
                    ) : (
                      <QrCode size={30} strokeWidth={1.8} />
                    )}
                  </div>
                  <div className="settings-logo-upload-copy">
                    <p>QR de cobro</p>
                    <span>Sube una captura o imagen del QR. Antes de guardarlo podras recortar solo el codigo para los documentos comerciales.</span>
                    {paymentQrError && <strong>{paymentQrError}</strong>}
                  </div>
                  <div className="settings-logo-upload-actions">
                    <input
                      ref={paymentQrInputRef}
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      onChange={handlePaymentQrChange}
                      className="sr-only"
                    />
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => paymentQrInputRef.current?.click()}
                      disabled={uploadingPaymentQr}
                    >
                      {uploadingPaymentQr ? (
                        <>
                          <Spinner size="sm" /> Subiendo...
                        </>
                      ) : (
                        <>
                          <ImageUp size={15} /> Subir captura QR
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <div className="settings-tax-identity-card">
                  <div className="settings-ruc-lock-card">
                    <span>RUC emisor</span>
                    <strong>{tenantData?.business_ruc || 'No configurado'}</strong>
                    <p>Bloqueado para el tenant: cambiarlo exige revalidar token, certificado y credenciales fiscales.</p>
                  </div>
                  <div className="settings-tax-identity-grid">
                    <FormField
                      label="Razón social SUNAT"
                      icon={Building2}
                      hint={`Debe coincidir con SUNAT. Máximo ${BUSINESS_NAME_MAX_LENGTH} caracteres.`}
                      error={businessErrors.business_name}
                      required
                    >
                      <input
                        className={`input${businessErrors.business_name ? ' input-error' : ''}`}
                        value={businessName}
                        onChange={(event) => {
                          const nextName = event.target.value;
                          setBusinessName(nextName);
                          setBusinessErrors((current) => ({
                            ...current,
                            business_name: validateBusinessName(nextName),
                          }));
                        }}
                        maxLength={BUSINESS_NAME_MAX_LENGTH}
                        placeholder="Razón social registrada en SUNAT"
                      />
                    </FormField>
                    <FormField
                      label="Domicilio fiscal SUNAT"
                      icon={FileCheck2}
                      hint={`Debe corresponder al domicilio fiscal vigente. Maximo ${BUSINESS_ADDRESS_MAX_LENGTH} caracteres.`}
                      error={businessErrors.business_address}
                      required
                    >
                      <textarea
                        className={`input settings-textarea${businessErrors.business_address ? ' input-error' : ''}`}
                        value={businessAddress}
                        onChange={(event) => {
                          const nextAddress = event.target.value;
                          setBusinessAddress(nextAddress);
                          setBusinessErrors((current) => ({
                            ...current,
                            business_address: validateBusinessAddress(nextAddress),
                          }));
                        }}
                        maxLength={BUSINESS_ADDRESS_MAX_LENGTH}
                        placeholder="Domicilio fiscal registrado en SUNAT"
                        rows={3}
                      />
                    </FormField>
                  </div>
                </div>

                <FormField
                  label="Teléfono de contacto"
                  icon={Phone}
                  hint="Celular peruano: 9 dígitos numéricos que inicia en 9."
                  error={phoneError}
                  className="settings-contact-field"
                >
                  <input
                    className={`input${phoneError ? ' input-error' : ''}`}
                    value={phone}
                    onChange={(event) => {
                      const nextPhone = normalizePeruMobileInput(event.target.value);
                      setPhone(nextPhone);
                      setPhoneError(validatePeruMobilePhone(nextPhone, 'Teléfono de contacto'));
                    }}
                    placeholder="+51 999 999 999"
                    inputMode="numeric"
                  />
                </FormField>

                <div>
                  <div className="settings-payment-toolbar">
                    <div>
                      <p className="settings-payment-title">Datos para la transferencia</p>
                      <span>Agrega cuentas bancarias o billeteras que saldran en el pie del PDF.</span>
                    </div>
                    <button type="button" onClick={() => addPaymentMethod('bank')} className="btn-secondary">
                      + Cuenta bancaria
                    </button>
                    <button type="button" onClick={() => addPaymentMethod('wallet')} className="btn-secondary">
                      + Billetera digital
                    </button>
                  </div>
                  {paymentMethods.length > 0 ? (
                    <div className="space-y-3">
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
                    <div className="hint-card">
                      <CreditCard size={14} className="flex-shrink-0" />
                      <span>Todavia no hay cuentas bancarias ni billeteras digitales configuradas.</span>
                    </div>
                  )}
                </div>

                <div className="settings-share-template-card">
                  <div className="settings-share-template-header">
                    <div className="settings-section-title">
                      <div className="settings-icon-box">
                        <MessageCircle size={15} />
                      </div>
                      <div>
                        <h3>Mensajes para compartir</h3>
                        <p>Personaliza el texto que se abre al enviar cotizaciones por WhatsApp o correo.</p>
                      </div>
                    </div>
                    <button type="button" className="btn-secondary" onClick={resetCommunicationTemplates}>
                      Restaurar texto base
                    </button>
                  </div>

                  <div className="settings-share-placeholder-row" aria-label="Variables disponibles">
                    {SHARE_TEMPLATE_PLACEHOLDERS.map((placeholder) => (
                      <code key={placeholder}>{placeholder}</code>
                    ))}
                  </div>

                  <div className="settings-share-template-grid">
                    <FormField
                      label="Mensaje WhatsApp"
                      icon={MessageCircle}
                      hint="Incluye {url} para que el cliente reciba el enlace del PDF."
                    >
                      <textarea
                        className="input settings-textarea settings-share-textarea"
                        value={communicationTemplates.whatsapp_message}
                        onChange={setCommunicationTemplateField('whatsapp_message')}
                        maxLength={1200}
                        rows={7}
                      />
                    </FormField>

                    <div className="settings-email-template-stack">
                      <FormField label="Asunto del correo" icon={Mail}>
                        <input
                          className="input"
                          value={communicationTemplates.email_subject}
                          onChange={setCommunicationTemplateField('email_subject')}
                          maxLength={180}
                        />
                      </FormField>
                      <FormField label="Cuerpo del correo" icon={Mail}>
                        <textarea
                          className="input settings-textarea settings-share-textarea"
                          value={communicationTemplates.email_body}
                          onChange={setCommunicationTemplateField('email_body')}
                          maxLength={3000}
                          rows={7}
                        />
                      </FormField>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
                    {saving && <Spinner size="sm" />} Guardar cambios
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {activeTab === 'fiscal' && (
        <div className={`settings-view settings-tab-panel settings-tab-panel--${tabDirection}`}>
          <div className="settings-rail-card settings-panel settings-fiscal-panel">
            <div className="settings-rail-card-header">
              <div className="settings-section-title">
                <div className="settings-icon-box">
                  <ShieldCheck size={15} />
                </div>
                <div>
                  <h3>Estado de credenciales fiscales</h3>
                  <p>Checklist de requisitos para emitir comprobantes y firmar XML sin exponer secretos al usuario.</p>
                </div>
              </div>
              <div className="settings-fiscal-score">
                <strong>{fiscalConfiguredCount}/4</strong>
                <span>requisitos listos</span>
              </div>
            </div>
            <div className="settings-fiscal-overview">
              <div>
                <span className="settings-fiscal-kicker">Estado fiscal</span>
                <strong>{fiscalReady ? 'Emisión lista' : 'Configuración parcial'}</strong>
                <p>
                  {fiscalReady
                    ? 'El tenant tiene credenciales y certificado para operar documentos fiscales.'
                    : 'Faltan requisitos antes de considerar completa la emisión fiscal.'}
                </p>
              </div>
              <span className={`status-pill ${fiscalReady ? 'ok' : 'warn'}`}>
                {fiscalReady ? 'Operativo' : 'Revision requerida'}
              </span>
            </div>
            <div className="credential-status-grid">
              <FiscalStatusTile
                icon={BadgeCheck}
                tone={hasSmartPseCpeCredentials ? 'ok' : 'missing'}
                label="Smart PSE CPE"
                value="Proveedor fiscal demo"
              >
                <StatusBadge ok={hasSmartPseCpeCredentials} labelOk="Configurado" labelNo="No configurado" />
              </FiscalStatusTile>
              <FiscalStatusTile
                icon={RadioTower}
                tone={tenantData?.has_sunat_credentials ? 'ok' : 'pending'}
                label="Credenciales fiscales gestionadas"
                value="SUNAT / GRE"
              >
                <StatusBadge
                  ok={tenantData?.has_sunat_credentials}
                  pending={!tenantData?.has_sunat_credentials}
                  labelOk="Configuradas"
                  labelPending="Pendiente"
                  labelNo="Pendiente"
                />
                <p className="settings-fiscal-managed-note">
                  Solo superadmin puede cargar o rotar credenciales GRE/SUNAT.
                </p>
              </FiscalStatusTile>
              <FiscalStatusTile
                icon={FileKey2}
                tone={tenantData?.has_sunat_cert ? 'ok' : 'missing'}
                label="Certificado PFX"
                value="Firma electronica de XML"
              >
                <StatusBadge ok={tenantData?.has_sunat_cert} labelOk="Cargado" labelNo="No cargado" />
              </FiscalStatusTile>
              <FiscalStatusTile
                icon={FileCheck2}
                tone="ok"
                label="Modo de emisión"
                value="Entorno activo"
              >
                <span className="status-pill ok">Configurado por SA</span>
              </FiscalStatusTile>
            </div>
          </div>

          <div className="notice-card settings-fiscal-notice">
            <AlertTriangle size={15} className="flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-[13px] mb-1">Actualizacion restringida</p>
              <p className="text-[12px]">
                {isSuperadmin ? (
                  <>
                    Como superadmin, gestiona credenciales fiscales desde{' '}
                    <Link to="/superadmin" className="underline font-semibold">Superadmin</Link>.
                  </>
                ) : (
                  'Contacte al superadmin de la plataforma para configurar o rotar las credenciales fiscales.'
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'cuenta' && (
        <div className={`settings-view settings-tab-panel settings-tab-panel--${tabDirection}`}>
          <div className="account-card settings-panel settings-account-panel">
            <div className="account-head">
              <div className="account-avatar">
                {((user?.nombre_completo || user?.email || 'U')[0]).toUpperCase()}
              </div>
              <div>
                <p className="text-[15px] font-extrabold text-[var(--color-text)]">{user?.nombre_completo || user?.email}</p>
                <p className="text-[11px] font-mono uppercase tracking-[0.1em] text-[var(--color-text-muted)] mt-0.5">
                  {isSuperadmin ? 'superadmin' : user?.rol}
                </p>
              </div>
              <span className="settings-account-badge">
                {isSuperadmin ? 'Acceso interno' : 'Cuenta activa'}
              </span>
            </div>
            <div className="credential-list settings-account-list">
              <div className="credential-item settings-account-item">
                <span className="ci-label">Nombre completo</span>
                <span className="ci-value">{user?.nombre_completo || '--'}</span>
              </div>
              <div className="credential-item settings-account-item">
                <span className="ci-label">Email</span>
                <span className="ci-value">{user?.email}</span>
              </div>
              <div className="credential-item settings-account-item">
                <span className="ci-label">Rol</span>
                <span className="ci-value">{isSuperadmin ? 'superadmin' : user?.rol}</span>
              </div>
              <div className="credential-item settings-account-item settings-account-security">
                <span className="ci-label">Seguridad</span>
                <button
                  type="button"
                  onClick={() => handleTabChange('seguridad')}
                  className="btn-secondary settings-inline-action"
                >
                  Cambiar contraseña
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'seguridad' && (
        <div className={`settings-tab-panel settings-tab-panel--${tabDirection}`}>
          <SeguridadPanel />
        </div>
      )}

      {activeTab === 'apariencia' && (
        <div className={`settings-tab-panel settings-tab-panel--${tabDirection}`}>
          <AparienciaPanel tenantData={tenantData} />
        </div>
      )}

      <PaymentQrCropper
        open={Boolean(paymentQrCropFile)}
        file={paymentQrCropFile}
        uploading={uploadingPaymentQr}
        onCancel={() => {
          if (!uploadingPaymentQr) setPaymentQrCropFile(null);
        }}
        onConfirm={handlePaymentQrCropConfirm}
      />
    </div>
  );
}
