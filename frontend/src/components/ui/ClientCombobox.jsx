/**
 * ClientCombobox v5 — inline client search, all fields always visible.
 *
 * Behaviour:
 *  - Typing in Número or Razón Social searches local DB in real time (portal dropdown).
 *  - Selecting fills all fields and locks identity (tipo_doc, numero, razon_social).
 *  - Contact fields (email, telefono, direccion) are ALWAYS editable.
 *    Editing them while an existing client is selected sets isDirty=true so
 *    the parent can PUT the client inside upsertCliente() when saving.
 *  - When the user types a new client name/number without selecting a match,
 *    the component marks isNew=true; the parent creates the client on save
 *    via upsertCliente() — no intermediate "Registrar" button needed.
 *  - email and telefono are OPTIONAL — they do not block save.
 *  - onFormChange(formData, { isDirty, isNew, id }) fires on every field change.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Search, X, Loader2 } from 'lucide-react';
import { clientes as cliSvc } from '../../services/clientes';
import CustomSelect from './CustomSelect';
import { normalizePeruMobileInput, validatePeruMobilePhone } from '../../lib/utils/peruPhoneValidation';

const DOC_TYPES = [
  { value: '6', label: 'RUC' },
  { value: '1', label: 'DNI' },
  { value: '4', label: 'CE' },
  { value: '7', label: 'PAS' },
];

function docLabel(tipo) {
  return DOC_TYPES.find((d) => d.value === tipo)?.label || 'DOC';
}

const EMPTY = {
  tipo_documento: '6',
  numero_documento: '',
  razon_social: '',
  email: '',
  telefono: '',
  direccion: '',
};

const labelSt = {
  display: 'block', fontSize: '10px', fontWeight: 700, color: '#64748B',
  textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px',
};

const roLabelSt = { ...labelSt, color: '#94A3B8' };

const inputSt = (locked) => ({
  width: '100%', height: '36px', fontFamily: 'var(--font-body)', fontSize: '13px',
  padding: '0 10px', border: `1.5px solid ${locked ? '#E2E8F0' : '#CBD5E1'}`,
  background: locked ? '#F8FAFC' : '#fff', color: locked ? '#475569' : '#0F172A',
  outline: 'none', boxSizing: 'border-box',
  cursor: locked ? 'default' : 'text', fontWeight: locked ? 600 : 400,
});

const errSt  = { fontSize: '11px', color: '#DC2626', marginTop: '3px' };
const warnSt = { fontSize: '11px', color: '#F59E0B', marginTop: '3px', fontWeight: 600 };

export default function ClientCombobox({
  clients = [],
  value,
  onChange,
  onFormChange,           // (formData, { isDirty, isNew, id }) => void
  quoteCountByClient = {},
  recentClientIds = [],
}) {
  const [form, setForm]               = useState(EMPTY);
  const [locked, setLocked]           = useState(false);
  const [isDirty, setIsDirty]         = useState(false);
  const [isNew, setIsNew]             = useState(false);
  const [activeField, setActiveField] = useState(null); // 'numero' | 'nombre'
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0, width: 0 });
  const [errors, setErrors]           = useState({});
  const [lookingUp, setLookingUp]     = useState(false);

  const numeroRef    = useRef(null);
  const nombreRef    = useRef(null);
  const dropdownRef  = useRef(null);
  const containerRef = useRef(null);

  const notify = useCallback((nextForm, nextLocked, nextIsDirty, nextIsNew) => {
    onFormChange?.(nextForm, { isDirty: nextIsDirty, isNew: nextIsNew, id: nextLocked ? value : null });
  }, [onFormChange, value]);

  // Sync when parent sets value externally (e.g. after upsert returns new id)
  useEffect(() => {
    if (!value) return;
    const found = clients.find((c) => String(c.id) === String(value));
    if (found) {
      const f = {
        tipo_documento:   found.tipo_documento || '6',
        numero_documento: found.numero_documento || '',
        razon_social:     found.razon_social || '',
        email:            found.email || '',
        telefono:         normalizePeruMobileInput(found.telefono || found.whatsapp || ''),
        direccion:        found.direccion || '',
      };
      setForm(f);
      setLocked(true);
      setIsDirty(false);
      setIsNew(false);
      notify(f, true, false, false);
    }
  }, [value, clients]); // eslint-disable-line react-hooks/exhaustive-deps

  function fillFromClient(client) {
    const f = {
      tipo_documento:   client.tipo_documento || '6',
      numero_documento: client.numero_documento || '',
      razon_social:     client.razon_social || '',
      email:            client.email || '',
      telefono:         normalizePeruMobileInput(client.telefono || client.whatsapp || ''),
      direccion:        client.direccion || '',
    };
    setForm(f);
    setLocked(true);
    setIsDirty(false);
    setIsNew(false);
    setActiveField(null);
    setErrors({});
    notify(f, true, false, false);
  }

  const matchedClients = useCallback((field, q) => {
    if (!q.trim()) return [];
    const low = q.toLowerCase();
    return clients.filter((c) =>
      field === 'numero'
        ? (c.numero_documento || '').toLowerCase().includes(low)
        : (c.razon_social || '').toLowerCase().includes(low),
    ).slice(0, 12);
  }, [clients]);

  const dropdownList = activeField
    ? matchedClients(activeField, activeField === 'numero' ? form.numero_documento : form.razon_social)
    : [];

  const openFor = (field) => {
    const ref = field === 'numero' ? numeroRef : nombreRef;
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    setDropdownPos({ top: r.bottom + window.scrollY + 3, left: r.left + window.scrollX, width: Math.max(r.width, 320) });
    setActiveField(field);
  };

  useEffect(() => {
    if (!activeField) return;
    const handle = (e) => {
      if (!containerRef.current?.contains(e.target) && !dropdownRef.current?.contains(e.target)) {
        setActiveField(null);
        // If the user typed something without picking a match → mark as new
        if (!locked && (form.numero_documento.trim() || form.razon_social.trim())) {
          setIsNew(true);
          notify(form, false, false, true);
        }
      }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [activeField, locked, form, notify]);

  const setField = (k, v) => {
    const nextValue = k === 'telefono' ? normalizePeruMobileInput(v) : v;
    const next = { ...form, [k]: nextValue };
    setForm(next);
    setErrors((e) => {
      const nextErrors = { ...e, [k]: undefined };
      if (k === 'telefono') {
        nextErrors.telefono = validatePeruMobilePhone(nextValue, 'Telefono / WhatsApp') || undefined;
      }
      return nextErrors;
    });

    const contactFields = ['email', 'telefono', 'direccion'];
    if (locked && contactFields.includes(k)) {
      setIsDirty(true);
      notify(next, true, true, false);
    } else {
      notify(next, locked, isDirty, isNew);
    }
  };

  const handleNumeroChange = (e) => {
    setField('numero_documento', e.target.value);
    if (locked) { onChange(''); setLocked(false); setIsDirty(false); setIsNew(false); }
    openFor('numero');
  };

  const handleNombreChange = (e) => {
    setField('razon_social', e.target.value);
    if (locked) { onChange(''); setLocked(false); setIsDirty(false); setIsNew(false); }
    openFor('nombre');
  };

  const handleSelectClient = (client) => {
    onChange(String(client.id));
    fillFromClient(client);
  };

  const handleClear = () => {
    onChange('');
    setForm(EMPTY);
    setLocked(false);
    setIsDirty(false);
    setIsNew(false);
    setErrors({});
    setActiveField(null);
    notify(EMPTY, false, false, false);
    setTimeout(() => numeroRef.current?.focus(), 0);
  };

  const handleLookup = async () => {
    const num = form.numero_documento.trim();
    if (!num) return;
    const found = clients.find((c) => c.numero_documento === num);
    if (found) { handleSelectClient(found); return; }
    setLookingUp(true);
    try {
      const data = await cliSvc.lookupDocument(num);
      const next = {
        ...form,
        razon_social: data.razon_social || data.nombre || form.razon_social,
        direccion:    data.direccion || form.direccion,
      };
      setForm(next);
      notify(next, locked, isDirty, isNew);
    } catch {
      // silent
    } finally {
      setLookingUp(false);
    }
  };

  // Validation: only identity fields are required; email/telefono are optional
  const validate = () => {
    const errs = {};
    if (!form.numero_documento.trim()) errs.numero_documento = 'Requerido';
    if (!form.razon_social.trim())     errs.razon_social = 'Requerido';
    // Email: only validate format if user wrote something
    if (form.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      errs.email = 'Formato inválido';
    }
    const phoneError = validatePeruMobilePhone(form.telefono, 'Telefono / WhatsApp');
    if (phoneError) errs.telefono = phoneError;
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const canLookup  = form.tipo_documento === '6' || form.tipo_documento === '1';
  const hasNewData = !locked && (form.numero_documento.trim() || form.razon_social.trim());

  return (
    <div ref={containerRef}>

      {/* ── Row 1: Tipo + Número + Nombre ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr 1fr', gap: '10px', marginBottom: '10px', alignItems: 'start' }}>

        {/* Tipo documento */}
        <div>
          <label style={locked ? roLabelSt : labelSt}>Tipo doc.</label>
          {locked ? (
            <input readOnly style={inputSt(true)} value={docLabel(form.tipo_documento)} />
          ) : (
            <CustomSelect
              compact
              value={form.tipo_documento}
              onChange={(v) => setField('tipo_documento', v)}
              options={DOC_TYPES}
            />
          )}
        </div>

        {/* Número documento */}
        <div>
          <label style={locked ? roLabelSt : labelSt}>
            Número doc. {!locked && <span style={{ color: '#DC2626' }}>*</span>}
          </label>
          <div style={{ position: 'relative', display: 'flex', gap: '6px' }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <input
                ref={numeroRef}
                readOnly={locked}
                style={{ ...inputSt(locked), paddingRight: locked ? '32px' : '10px' }}
                value={form.numero_documento}
                onChange={handleNumeroChange}
                onFocus={() => { if (!locked) openFor('numero'); }}
                placeholder={!locked ? (form.tipo_documento === '6' ? '20xxxxxxxxx' : '8 dígitos') : ''}
                maxLength={form.tipo_documento === '6' ? 11 : form.tipo_documento === '1' ? 8 : 20}
              />
              {locked && (
                <button type="button" onClick={handleClear} title="Cambiar cliente"
                  style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#94A3B8', display: 'flex', padding: '2px' }}>
                  <X size={13} />
                </button>
              )}
            </div>
            {!locked && canLookup && (
              <button type="button" onClick={handleLookup} disabled={lookingUp || !form.numero_documento.trim()} title="Buscar en SUNAT / BD"
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '36px', height: '36px', flexShrink: 0, background: '#EEF2FF', border: '1.5px solid #C7D2FE', color: '#4338CA', cursor: lookingUp ? 'wait' : 'pointer' }}>
                {lookingUp ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Search size={13} />}
              </button>
            )}
          </div>
          {errors.numero_documento && <p style={errSt}>{errors.numero_documento}</p>}
        </div>

        {/* Razón social */}
        <div>
          <label style={locked ? roLabelSt : labelSt}>
            Razón social / Nombre {!locked && <span style={{ color: '#DC2626' }}>*</span>}
          </label>
          <input
            ref={nombreRef}
            readOnly={locked}
            style={inputSt(locked)}
            value={form.razon_social}
            onChange={handleNombreChange}
            onFocus={() => { if (!locked) openFor('nombre'); }}
            placeholder={!locked ? 'Escribe para buscar...' : ''}
          />
          {errors.razon_social && <p style={errSt}>{errors.razon_social}</p>}
        </div>
      </div>

      {/* ── Row 2: Correo + Teléfono (always editable, optional) ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px', alignItems: 'start' }}>
        <div>
          <label style={labelSt}>
            Correo electrónico
            <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, marginLeft: '4px', fontSize: '10px' }}>(opcional)</span>
            {locked && isDirty && <span style={{ color: '#F59E0B', marginLeft: '6px', fontSize: '9px', fontWeight: 700 }}>EDITADO</span>}
          </label>
          <input
            type="email"
            style={inputSt(false)}
            value={form.email}
            onChange={(e) => setField('email', e.target.value)}
            placeholder="cliente@empresa.com"
          />
          {errors.email && <p style={errSt}>{errors.email}</p>}
          {locked && !form.email && <p style={warnSt}>Sin correo registrado</p>}
        </div>
        <div>
          <label style={labelSt}>
            Teléfono / WhatsApp
            <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, marginLeft: '4px', fontSize: '10px' }}>(opcional)</span>
            {locked && isDirty && <span style={{ color: '#F59E0B', marginLeft: '6px', fontSize: '9px', fontWeight: 700 }}>EDITADO</span>}
          </label>
          <input
            type="tel"
            style={inputSt(false)}
            value={form.telefono}
            onChange={(e) => setField('telefono', e.target.value)}
            placeholder="9xxxxxxxx"
          />
          {errors.telefono && <p style={errSt}>{errors.telefono}</p>}
          {locked && !form.telefono && <p style={warnSt}>Sin teléfono registrado</p>}
        </div>
      </div>

      {/* ── Row 3: Dirección (always editable, optional) ── */}
      <div style={{ marginBottom: '10px' }}>
        <label style={labelSt}>
          Dirección
          <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, marginLeft: '4px', fontSize: '10px' }}>(opcional)</span>
          {locked && isDirty && <span style={{ color: '#F59E0B', marginLeft: '6px', fontSize: '9px', fontWeight: 700 }}>EDITADO</span>}
        </label>
        <input
          style={inputSt(false)}
          value={form.direccion}
          onChange={(e) => setField('direccion', e.target.value)}
          placeholder="Av. ..."
        />
      </div>

      {/* ── Status notices ── */}
      {locked && isDirty && (
        <p style={{ fontSize: '11px', color: '#4F46E5', marginBottom: '8px' }}>
          Los cambios en correo, teléfono o dirección <strong>actualizarán al cliente</strong> en el catálogo al guardar.
        </p>
      )}
      {hasNewData && !locked && (
        <p style={{ fontSize: '11px', color: '#64748B', marginBottom: '4px' }}>
          Nuevo cliente — <span style={{ color: '#4F46E5', fontWeight: 600 }}>se registrará al guardar la cotización</span>.
        </p>
      )}

      {/* Error from parent-level submit validation */}
      {errors._ && <p style={{ ...errSt, marginBottom: '4px' }}>{errors._}</p>}

      {/* ── Dropdown portal ── */}
      {activeField && dropdownList.length > 0 && createPortal(
        <div ref={dropdownRef}
          style={{ position: 'absolute', top: dropdownPos.top, left: dropdownPos.left, width: Math.max(dropdownPos.width, 320), background: '#fff', border: '1.5px solid #C7D2FE', boxShadow: '0 8px 24px rgba(0,0,0,0.12)', zIndex: 9999, maxHeight: '260px', overflowY: 'auto' }}>
          {dropdownList.map((client) => {
            const isFreq   = (quoteCountByClient[client.id] || 0) >= 3;
            const isRecent = recentClientIds.includes(client.id);
            return (
              <button key={client.id} type="button"
                onMouseDown={(e) => { e.preventDefault(); handleSelectClient(client); }}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', padding: '9px 14px', border: 'none', borderBottom: '1px solid #F1F5F9', background: '#fff', cursor: 'pointer', textAlign: 'left', gap: '12px' }}
                onMouseEnter={(e) => { e.currentTarget.style.background = '#F8FAFC'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = '#fff'; }}>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontWeight: 600, fontSize: '13px', color: '#0F172A', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{client.razon_social}</p>
                  <p style={{ fontSize: '11px', color: '#64748B', fontFamily: 'var(--font-mono)' }}>
                    {docLabel(client.tipo_documento)} {client.numero_documento}{client.email ? ` · ${client.email}` : ''}
                  </p>
                </div>
                {(isRecent || isFreq) && (
                  <span style={{ flexShrink: 0, padding: '2px 8px', fontSize: '9px', fontWeight: 700, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', background: isRecent ? '#EEF2FF' : '#F8FAFC', color: isRecent ? '#4338CA' : '#475569', border: `1px solid ${isRecent ? '#C7D2FE' : '#E2E8F0'}` }}>
                    {isRecent ? 'Nuevo' : 'Frecuente'}
                  </span>
                )}
              </button>
            );
          })}
        </div>,
        document.body,
      )}
    </div>
  );
}
