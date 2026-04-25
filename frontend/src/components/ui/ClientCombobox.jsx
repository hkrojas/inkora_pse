/**
 * ClientCombobox v5: inline client search, all fields always visible.
 *
 * Behaviour:
 *  - Typing in Numero or Razon Social searches local DB in real time.
 *  - Selecting fills all fields and locks identity.
 *  - Contact fields remain editable.
 *  - Editing contact fields on a locked client sets isDirty=true.
 *  - Typing a new client without selecting a match marks isNew=true.
 *  - Email and telefono are optional.
 *  - onFormChange(formData, { isDirty, isNew, id }) fires on every change.
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

export default function ClientCombobox({
  clients = [],
  value,
  onChange,
  onFormChange,
  quoteCountByClient = {},
  recentClientIds = [],
}) {
  const [form, setForm] = useState(EMPTY);
  const [locked, setLocked] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [isNew, setIsNew] = useState(false);
  const [activeField, setActiveField] = useState(null);
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0, width: 0 });
  const [errors, setErrors] = useState({});
  const [lookingUp, setLookingUp] = useState(false);

  const numeroRef = useRef(null);
  const nombreRef = useRef(null);
  const dropdownRef = useRef(null);
  const containerRef = useRef(null);

  const notify = useCallback((nextForm, nextLocked, nextIsDirty, nextIsNew) => {
    onFormChange?.(nextForm, { isDirty: nextIsDirty, isNew: nextIsNew, id: nextLocked ? value : null });
  }, [onFormChange, value]);

  useEffect(() => {
    if (!value) return;
    const found = clients.find((c) => String(c.id) === String(value));
    if (found) {
      const nextForm = {
        tipo_documento: found.tipo_documento || '6',
        numero_documento: found.numero_documento || '',
        razon_social: found.razon_social || '',
        email: found.email || '',
        telefono: normalizePeruMobileInput(found.telefono || found.whatsapp || ''),
        direccion: found.direccion || '',
      };
      setForm(nextForm);
      setLocked(true);
      setIsDirty(false);
      setIsNew(false);
      notify(nextForm, true, false, false);
    }
  }, [value, clients]); // eslint-disable-line react-hooks/exhaustive-deps

  function fillFromClient(client) {
    const nextForm = {
      tipo_documento: client.tipo_documento || '6',
      numero_documento: client.numero_documento || '',
      razon_social: client.razon_social || '',
      email: client.email || '',
      telefono: normalizePeruMobileInput(client.telefono || client.whatsapp || ''),
      direccion: client.direccion || '',
    };
    setForm(nextForm);
    setLocked(true);
    setIsDirty(false);
    setIsNew(false);
    setActiveField(null);
    setErrors({});
    notify(nextForm, true, false, false);
  }

  const matchedClients = useCallback((field, query) => {
    if (!query.trim()) return [];
    const low = query.toLowerCase();
    return clients.filter((client) =>
      field === 'numero'
        ? (client.numero_documento || '').toLowerCase().includes(low)
        : (client.razon_social || '').toLowerCase().includes(low),
    ).slice(0, 12);
  }, [clients]);

  const dropdownList = activeField
    ? matchedClients(activeField, activeField === 'numero' ? form.numero_documento : form.razon_social)
    : [];

  const openFor = (field) => {
    const ref = field === 'numero' ? numeroRef : nombreRef;
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    setDropdownPos({
      top: rect.bottom + window.scrollY + 3,
      left: rect.left + window.scrollX,
      width: Math.max(rect.width, 320),
    });
    setActiveField(field);
  };

  useEffect(() => {
    if (!activeField) return;
    const handle = (event) => {
      if (!containerRef.current?.contains(event.target) && !dropdownRef.current?.contains(event.target)) {
        setActiveField(null);
        if (!locked && (form.numero_documento.trim() || form.razon_social.trim())) {
          setIsNew(true);
          notify(form, false, false, true);
        }
      }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [activeField, locked, form, notify]);

  const setField = (key, rawValue) => {
    const nextValue = key === 'telefono' ? normalizePeruMobileInput(rawValue) : rawValue;
    const nextForm = { ...form, [key]: nextValue };
    setForm(nextForm);
    setErrors((current) => {
      const nextErrors = { ...current, [key]: undefined };
      if (key === 'telefono') {
        nextErrors.telefono = validatePeruMobilePhone(nextValue, 'Telefono / WhatsApp') || undefined;
      }
      return nextErrors;
    });

    const contactFields = ['email', 'telefono', 'direccion'];
    if (locked && contactFields.includes(key)) {
      setIsDirty(true);
      notify(nextForm, true, true, false);
    } else {
      notify(nextForm, locked, isDirty, isNew);
    }
  };

  const handleNumeroChange = (event) => {
    setField('numero_documento', event.target.value);
    if (locked) {
      onChange('');
      setLocked(false);
      setIsDirty(false);
      setIsNew(false);
    }
    openFor('numero');
  };

  const handleNombreChange = (event) => {
    setField('razon_social', event.target.value);
    if (locked) {
      onChange('');
      setLocked(false);
      setIsDirty(false);
      setIsNew(false);
    }
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
    const found = clients.find((client) => client.numero_documento === num);
    if (found) {
      handleSelectClient(found);
      return;
    }
    setLookingUp(true);
    try {
      const data = await cliSvc.lookupDocument(num);
      const nextForm = {
        ...form,
        razon_social: data.razon_social || data.nombre || form.razon_social,
        direccion: data.direccion || form.direccion,
      };
      setForm(nextForm);
      notify(nextForm, locked, isDirty, isNew);
    } catch {
      // silent
    } finally {
      setLookingUp(false);
    }
  };

  const validate = () => {
    const nextErrors = {};
    if (!form.numero_documento.trim()) nextErrors.numero_documento = 'Requerido';
    if (!form.razon_social.trim()) nextErrors.razon_social = 'Requerido';
    if (form.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      nextErrors.email = 'Formato invalido';
    }
    const phoneError = validatePeruMobilePhone(form.telefono, 'Telefono / WhatsApp');
    if (phoneError) nextErrors.telefono = phoneError;
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const canLookup = form.tipo_documento === '6' || form.tipo_documento === '1';
  const hasNewData = !locked && (form.numero_documento.trim() || form.razon_social.trim());

  return (
    <div ref={containerRef}>
      <div className="mb-2 grid items-start gap-2 md:grid-cols-[130px_minmax(0,1fr)_minmax(0,1fr)]">
        <div>
          <label className={locked ? 'label client-combobox-label-muted' : 'label'}>Tipo doc.</label>
          {locked ? (
            <input readOnly className="input client-combobox-input client-combobox-input--locked" value={docLabel(form.tipo_documento)} />
          ) : (
            <CustomSelect
              compact
              value={form.tipo_documento}
              onChange={(nextValue) => setField('tipo_documento', nextValue)}
              options={DOC_TYPES}
            />
          )}
        </div>

        <div>
          <label className={locked ? 'label client-combobox-label-muted' : 'label'}>
            Numero doc. {!locked && <span className="text-[var(--color-error)]">*</span>}
          </label>
          <div className="client-combobox-field-row">
            <div className="client-combobox-input-wrap">
              <input
                ref={numeroRef}
                readOnly={locked}
                className={`input client-combobox-input ${locked ? 'client-combobox-input--locked pr-8 font-mono' : ''}`}
                value={form.numero_documento}
                onChange={handleNumeroChange}
                onFocus={() => { if (!locked) openFor('numero'); }}
                placeholder={!locked ? (form.tipo_documento === '6' ? '20xxxxxxxxx' : '8 digitos') : ''}
                maxLength={form.tipo_documento === '6' ? 11 : form.tipo_documento === '1' ? 8 : 20}
              />
              {locked && (
                <button type="button" onClick={handleClear} title="Cambiar cliente" className="client-combobox-clear-btn">
                  <X size={13} />
                </button>
              )}
            </div>
            {!locked && canLookup && (
              <button
                type="button"
                onClick={handleLookup}
                disabled={lookingUp || !form.numero_documento.trim()}
                title="Buscar en SUNAT / BD"
                className="client-combobox-lookup-btn"
              >
                {lookingUp ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Search size={13} />}
              </button>
            )}
          </div>
          {errors.numero_documento && <p className="client-combobox-error">{errors.numero_documento}</p>}
        </div>

        <div>
          <label className={locked ? 'label client-combobox-label-muted' : 'label'}>
            Razon social / Nombre {!locked && <span className="text-[var(--color-error)]">*</span>}
          </label>
          <input
            ref={nombreRef}
            readOnly={locked}
            className={`input client-combobox-input ${locked ? 'client-combobox-input--locked' : ''}`}
            value={form.razon_social}
            onChange={handleNombreChange}
            onFocus={() => { if (!locked) openFor('nombre'); }}
            placeholder={!locked ? 'Escribe para buscar...' : ''}
          />
          {errors.razon_social && <p className="client-combobox-error">{errors.razon_social}</p>}
        </div>
      </div>

      <div className="mb-2 grid items-start gap-2 md:grid-cols-2">
        <div>
          <label className="label">
            Correo electronico
            <span className="client-combobox-label-note">(opcional)</span>
            {locked && isDirty && <span className="client-combobox-label-edit">EDITADO</span>}
          </label>
          <input
            type="email"
            className="input client-combobox-input"
            value={form.email}
            onChange={(event) => setField('email', event.target.value)}
            placeholder="cliente@empresa.com"
          />
          {errors.email && <p className="client-combobox-error">{errors.email}</p>}
          {locked && !form.email && <p className="client-combobox-status client-combobox-status--warning">Sin correo registrado</p>}
        </div>

        <div>
          <label className="label">
            Telefono / WhatsApp
            <span className="client-combobox-label-note">(opcional)</span>
            {locked && isDirty && <span className="client-combobox-label-edit">EDITADO</span>}
          </label>
          <input
            type="tel"
            className="input client-combobox-input"
            value={form.telefono}
            onChange={(event) => setField('telefono', event.target.value)}
            placeholder="9xxxxxxxx"
          />
          {errors.telefono && <p className="client-combobox-error">{errors.telefono}</p>}
          {locked && !form.telefono && <p className="client-combobox-status client-combobox-status--warning">Sin telefono registrado</p>}
        </div>
      </div>

      <div className="mb-2">
        <label className="label">
          Direccion
          <span className="client-combobox-label-note">(opcional)</span>
          {locked && isDirty && <span className="client-combobox-label-edit">EDITADO</span>}
        </label>
        <input
          className="input client-combobox-input"
          value={form.direccion}
          onChange={(event) => setField('direccion', event.target.value)}
          placeholder="Av. ..."
        />
      </div>

      {locked && isDirty && (
        <p className="client-combobox-status client-combobox-status--dirty">
          Los cambios en correo, telefono o direccion <strong>actualizaran al cliente</strong> en el catalogo al guardar.
        </p>
      )}
      {hasNewData && !locked && (
        <p className="client-combobox-status client-combobox-status--new">
          Nuevo cliente - <span className="font-semibold text-[var(--ink-primary)]">se registrara al guardar la cotizacion</span>.
        </p>
      )}

      {errors._ && <p className="client-combobox-error mb-1">{errors._}</p>}

      {activeField && dropdownList.length > 0 && createPortal(
        <div
          ref={dropdownRef}
          className="ink-combobox-menu"
          style={{
            top: dropdownPos.top,
            left: dropdownPos.left,
            width: Math.max(dropdownPos.width, 320),
          }}
        >
          {dropdownList.map((client) => {
            const isFreq = (quoteCountByClient[client.id] || 0) >= 3;
            const isRecent = recentClientIds.includes(client.id);
            return (
              <button
                key={client.id}
                type="button"
                onMouseDown={(event) => { event.preventDefault(); handleSelectClient(client); }}
                className="ink-combobox-option"
              >
                <div className="ink-combobox-option-copy">
                  <p className="ink-combobox-option-title">{client.razon_social}</p>
                  <p className="ink-combobox-option-meta">
                    {docLabel(client.tipo_documento)} {client.numero_documento}{client.email ? ` · ${client.email}` : ''}
                  </p>
                </div>
                {(isRecent || isFreq) && (
                  <span className={`ink-combobox-pill ${isRecent ? 'ink-combobox-pill--recent' : ''}`}>
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
