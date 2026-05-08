/**
 * Inline client search/edit for quote flows.
 * Keeps fiscal identity fields strict because this data later feeds invoices/receipts.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Search, X, Loader2 } from 'lucide-react';
import { clientes as cliSvc } from '../../services/clientes';
import CustomSelect from './CustomSelect';
import {
  FISCAL_DOC_TYPE_OPTIONS,
  buildFiscalClientErrors,
  getFiscalDocLabel,
  getFiscalDocMeta,
  normalizeFiscalClientForm,
  normalizeFiscalDocumentNumber,
  normalizeFiscalUbigeo,
} from '../../lib/utils/fiscalClientValidation';

const EMPTY = {
  tipo_documento: '6',
  numero_documento: '',
  razon_social: '',
  nombre_comercial: '',
  email: '',
  telefono: '',
  direccion: '',
  ubigeo: '',
};

const SEARCH_DEBOUNCE_MS = 250;
const SEARCH_MIN_CHARS = 2;
const SEARCH_LIMIT = 20;

function clientKey(client) {
  if (client?.id !== undefined && client?.id !== null) return `id:${client.id}`;
  return `doc:${client?.numero_documento || ''}:${client?.razon_social || ''}`;
}

function mergeClients(...groups) {
  const seen = new Set();
  const merged = [];
  groups.flat().forEach((client) => {
    const key = clientKey(client);
    if (seen.has(key)) return;
    seen.add(key);
    merged.push(client);
  });
  return merged;
}

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
  const [remoteClients, setRemoteClients] = useState([]);

  const numeroRef = useRef(null);
  const nombreRef = useRef(null);
  const dropdownRef = useRef(null);
  const containerRef = useRef(null);
  const searchCacheRef = useRef(new Map());
  const searchAbortRef = useRef(null);

  const notify = useCallback((nextForm, nextLocked, nextIsDirty, nextIsNew) => {
    onFormChange?.(nextForm, { isDirty: nextIsDirty, isNew: nextIsNew, id: nextLocked ? value : null });
  }, [onFormChange, value]);

  useEffect(() => {
    if (!value) return;
    const found = mergeClients(clients, remoteClients).find((client) => String(client.id) === String(value));
    if (!found) return;
    const nextForm = normalizeFiscalClientForm(found);
    setForm(nextForm);
    setLocked(true);
    setIsDirty(false);
    setIsNew(false);
    setErrors({});
    notify(nextForm, true, false, false);
  }, [value, clients, remoteClients, notify]);

  const fillFromClient = useCallback((client) => {
    const nextForm = normalizeFiscalClientForm(client);
    setRemoteClients((current) => mergeClients([client], current));
    setForm(nextForm);
    setLocked(true);
    setIsDirty(false);
    setIsNew(false);
    setActiveField(null);
    setErrors({});
    notify(nextForm, true, false, false);
  }, [notify]);

  const matchedClients = useCallback((field, query, source = clients) => {
    if (!query.trim()) return [];
    const low = query.toLowerCase();
    return source.filter((client) => (
      field === 'numero'
        ? String(client.numero_documento || '').toLowerCase().includes(low)
        : String(client.razon_social || '').toLowerCase().includes(low)
    )).slice(0, 12);
  }, [clients]);

  const activeQuery = activeField === 'numero' ? form.numero_documento : form.razon_social;

  useEffect(() => {
    if (!activeField || locked) {
      searchAbortRef.current?.abort();
      setRemoteClients([]);
      return undefined;
    }

    const query = String(activeQuery || '').trim();
    if (query.length < SEARCH_MIN_CHARS) {
      searchAbortRef.current?.abort();
      setRemoteClients([]);
      return undefined;
    }

    const cacheKey = query.toLowerCase();
    const cached = searchCacheRef.current.get(cacheKey);
    if (cached) {
      setRemoteClients(cached);
      return undefined;
    }

    setRemoteClients([]);
    searchAbortRef.current?.abort();
    const controller = new AbortController();
    searchAbortRef.current = controller;

    const timerId = setTimeout(() => {
      cliSvc.search(query, SEARCH_LIMIT, { signal: controller.signal })
        .then((items) => {
          const results = Array.isArray(items) ? items : [];
          searchCacheRef.current.set(cacheKey, results);
          if (!controller.signal.aborted) setRemoteClients(results);
        })
        .catch((error) => {
          if (!error?.isCanceled && !controller.signal.aborted) setRemoteClients([]);
        })
        .finally(() => {
          if (searchAbortRef.current === controller) searchAbortRef.current = null;
        });
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      clearTimeout(timerId);
      controller.abort();
    };
  }, [activeField, activeQuery, locked]);

  const dropdownList = activeField
    ? mergeClients(
      matchedClients(activeField, activeQuery, remoteClients),
      matchedClients(activeField, activeQuery, clients),
    ).slice(0, 12)
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
    if (!activeField) return undefined;
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

  const validate = useCallback((nextForm = form) => {
    const nextErrors = buildFiscalClientErrors(nextForm);
    setErrors(nextErrors);
    return Object.values(nextErrors).every((error) => !error);
  }, [form]);

  const setField = (key, rawValue) => {
    const nextValue = key === 'telefono'
      ? rawValue.replace(/\D/g, '').slice(0, 9)
      : key === 'numero_documento'
        ? normalizeFiscalDocumentNumber(form.tipo_documento, rawValue)
        : key === 'ubigeo'
          ? normalizeFiscalUbigeo(rawValue)
          : rawValue;

    const nextForm = { ...form, [key]: nextValue };
    if (key === 'tipo_documento') {
      nextForm.numero_documento = normalizeFiscalDocumentNumber(nextValue, form.numero_documento);
    }

    setForm(nextForm);
    setErrors((current) => ({
      ...current,
      [key]: undefined,
      ...(key === 'tipo_documento'
        ? { numero_documento: undefined, direccion: undefined, ubigeo: undefined }
        : {}),
    }));

    const editableFields = ['email', 'telefono', 'direccion', 'ubigeo'];
    if (locked && editableFields.includes(key)) {
      setIsDirty(true);
      notify(nextForm, true, true, false);
      return;
    }
    notify(nextForm, locked, isDirty, isNew);
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
    const numero = form.numero_documento.trim();
    if (!numero) {
      validate({ ...form, numero_documento: '' });
      return;
    }

    const found = clients.find((client) => String(client.numero_documento || '').trim() === numero);
    if (found) {
      handleSelectClient(found);
      return;
    }

    setLookingUp(true);
    try {
      let remoteMatches = [];
      try {
        remoteMatches = await cliSvc.search(numero, 5);
      } catch {
        remoteMatches = [];
      }
      const remoteFound = (Array.isArray(remoteMatches) ? remoteMatches : [])
        .find((client) => String(client.numero_documento || '').trim() === numero);
      if (remoteFound) {
        handleSelectClient(remoteFound);
        return;
      }

      const data = await cliSvc.lookupDocument(numero);
      const nextForm = {
        ...form,
        tipo_documento: data.tipo === 'DNI' ? '1' : data.tipo === 'RUC' ? '6' : form.tipo_documento,
        razon_social: data.razon_social || data.nombre || form.razon_social,
        nombre_comercial: data.nombre_comercial || form.nombre_comercial,
        direccion: data.direccion && data.direccion !== '-' ? data.direccion : form.direccion,
        ubigeo: normalizeFiscalUbigeo(data.ubigeo || form.ubigeo),
      };
      setForm(nextForm);
      validate(nextForm);
      notify(nextForm, locked, isDirty, isNew);
    } catch {
      // keep the form editable; backend already exposes lookup detail elsewhere
    } finally {
      setLookingUp(false);
    }
  };

  const canLookup = getFiscalDocMeta(form.tipo_documento).lookupEnabled;
  const hasNewData = !locked && (form.numero_documento.trim() || form.razon_social.trim());

  return (
    <div ref={containerRef}>
      <div className="form-grid">
        <div className="field span-3">
          <label className={locked ? 'label client-combobox-label-muted' : 'label'}>Tipo doc.</label>
          {locked ? (
            <input
              readOnly
              className="input client-combobox-input client-combobox-input--locked"
              value={getFiscalDocLabel(form.tipo_documento)}
            />
          ) : (
            <CustomSelect
              compact
              value={form.tipo_documento}
              onChange={(nextValue) => setField('tipo_documento', nextValue)}
              options={FISCAL_DOC_TYPE_OPTIONS}
            />
          )}
        </div>

        <div className="field span-4">
          <label className={locked ? 'label client-combobox-label-muted' : 'label'}>
            Numero doc. {!locked && <span className="req">*</span>}
          </label>
          <div className="control-with-button">
            <div className="control" style={{ flex: 1, position: 'relative' }}>
              <input
                ref={numeroRef}
                readOnly={locked}
                className={`input client-combobox-input ${locked ? 'client-combobox-input--locked pr-8 font-mono' : ''}`}
                value={form.numero_documento}
                onChange={handleNumeroChange}
                onBlur={() => validate()}
                onFocus={() => { if (!locked) openFor('numero'); }}
                placeholder={!locked ? getFiscalDocMeta(form.tipo_documento).placeholder : ''}
                inputMode={getFiscalDocMeta(form.tipo_documento).inputMode}
                maxLength={getFiscalDocMeta(form.tipo_documento).maxLength}
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
                className="inline-btn"
              >
                {lookingUp ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Search size={13} />}
                Consultar
              </button>
            )}
          </div>
          {errors.numero_documento && <p className="client-combobox-error">{errors.numero_documento}</p>}
        </div>

        <div className="field span-5">
          <label className={locked ? 'label client-combobox-label-muted' : 'label'}>
            Razon social / Nombre {!locked && <span className="req">*</span>}
          </label>
          <div className="control">
            <input
              ref={nombreRef}
              readOnly={locked}
              className={`input client-combobox-input ${locked ? 'client-combobox-input--locked' : ''}`}
              value={form.razon_social}
              onChange={handleNombreChange}
              onBlur={() => validate()}
              onFocus={() => { if (!locked) openFor('nombre'); }}
              placeholder={!locked ? 'Escribe para buscar...' : ''}
            />
          </div>
          {errors.razon_social && <p className="client-combobox-error">{errors.razon_social}</p>}
        </div>

        <div className="field span-6">
          <label className="label">
            Correo electronico
            <span className="client-combobox-label-note">(opcional)</span>
            {locked && isDirty && <span className="client-combobox-label-edit">EDITADO</span>}
          </label>
          <div className="control">
            <input
              type="email"
              className="input client-combobox-input"
              value={form.email}
              onChange={(event) => setField('email', event.target.value)}
              onBlur={() => validate()}
              placeholder="cliente@empresa.com"
            />
          </div>
          {errors.email && <p className="client-combobox-error">{errors.email}</p>}
          {locked && !form.email && <p className="client-combobox-status client-combobox-status--warning">Sin correo registrado</p>}
        </div>

        <div className="field span-6">
          <label className="label">
            Telefono / WhatsApp
            <span className="client-combobox-label-note">(opcional)</span>
            {locked && isDirty && <span className="client-combobox-label-edit">EDITADO</span>}
          </label>
          <div className="control">
            <input
              type="tel"
              className="input client-combobox-input"
              value={form.telefono}
              onChange={(event) => setField('telefono', event.target.value)}
              onBlur={() => validate()}
              placeholder="9xxxxxxxx"
            />
          </div>
          {errors.telefono && <p className="client-combobox-error">{errors.telefono}</p>}
          {locked && !form.telefono && <p className="client-combobox-status client-combobox-status--warning">Sin telefono registrado</p>}
        </div>

        <div className="field span-8">
          <label className="label">
            Direccion fiscal
            <span className="client-combobox-label-note">
              {form.tipo_documento === '6' ? '(obligatoria para factura)' : '(opcional)'}
            </span>
            {locked && isDirty && <span className="client-combobox-label-edit">EDITADO</span>}
          </label>
          <div className="control">
            <input
              className="input client-combobox-input"
              value={form.direccion}
              onChange={(event) => setField('direccion', event.target.value)}
              onBlur={() => validate()}
              placeholder="Av. ..."
            />
          </div>
          {errors.direccion && <p className="client-combobox-error">{errors.direccion}</p>}
        </div>

        <div className="field span-4">
          <label className="label">
            Ubigeo
            <span className="client-combobox-label-note">
              {form.tipo_documento === '6' ? '(obligatorio)' : '(opcional)'}
            </span>
            {locked && isDirty && <span className="client-combobox-label-edit">EDITADO</span>}
          </label>
          <div className="control">
            <input
              className="input client-combobox-input"
              value={form.ubigeo}
              onChange={(event) => setField('ubigeo', event.target.value)}
              onBlur={() => validate()}
              inputMode="numeric"
              maxLength={6}
              placeholder="150101"
            />
          </div>
          {errors.ubigeo && <p className="client-combobox-error">{errors.ubigeo}</p>}
        </div>
      </div>

      {locked && isDirty && (
        <p className="client-combobox-status client-combobox-status--dirty" style={{ marginTop: '10px' }}>
          Los cambios en correo, telefono, direccion o ubigeo <strong>actualizaran al cliente</strong> en el catalogo al guardar.
        </p>
      )}
      {hasNewData && !locked && (
        <p className="client-combobox-status client-combobox-status--new" style={{ marginTop: '10px' }}>
          Nuevo cliente - <span className="font-semibold text-[var(--color-primary)]">se registrara al guardar la cotizacion</span>.
        </p>
      )}

      {errors._ && <p className="client-combobox-error mb-1">{errors._}</p>}

      {activeField && dropdownList.length > 0 && createPortal(
        <div
          ref={dropdownRef}
          className="ink-combobox-menu dropdown-enter"
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
                    {getFiscalDocLabel(client.tipo_documento)} {client.numero_documento}{client.email ? ` · ${client.email}` : ''}
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
