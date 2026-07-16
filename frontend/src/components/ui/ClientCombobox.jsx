/**
 * Inline client search/edit for quote flows.
 * Keeps fiscal identity fields strict because this data later feeds invoices/receipts.
 */
import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
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
import {
  getLookupAddress,
  getLookupCommercialName,
  getLookupDocumentType,
  getLookupName,
  getLookupUbigeo,
} from '../../lib/utils/documentLookup';
import { normalizeUppercaseFieldValue } from '../../lib/utils/uppercase';

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

function createEmptyForm(defaultDocumentType = '6') {
  return {
    ...EMPTY,
    tipo_documento: defaultDocumentType,
  };
}

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

function clientMatchesQuery(client, query) {
  const normalizedQuery = String(query || '').trim().toLowerCase();
  if (!normalizedQuery) return false;
  return [
    client?.numero_documento,
    client?.razon_social,
    client?.nombre_comercial,
    client?.email,
    client?.telefono,
    client?.whatsapp,
  ].some((value) => String(value || '').toLowerCase().includes(normalizedQuery));
}

export default function ClientCombobox({
  clients = [],
  value,
  onChange,
  onFormChange,
  quoteCountByClient = {},
  recentClientIds = [],
  defaultDocumentType = '6',
  allowedDocumentTypes = null,
}) {
  const allowedTypeSet = useMemo(() => (
    Array.isArray(allowedDocumentTypes) && allowedDocumentTypes.length
      ? new Set(allowedDocumentTypes.map((type) => String(type)))
      : null
  ), [allowedDocumentTypes]);
  const resolvedDefaultDocumentType = useMemo(() => (
    allowedTypeSet?.has(String(defaultDocumentType))
      ? String(defaultDocumentType)
      : Array.from(allowedTypeSet || [String(defaultDocumentType || '6')])[0]
  ), [allowedTypeSet, defaultDocumentType]);
  const isDocumentTypeAllowed = useCallback(
    (type) => !allowedTypeSet || allowedTypeSet.has(String(type || '')),
    [allowedTypeSet],
  );
  const documentTypeOptions = useMemo(
    () => FISCAL_DOC_TYPE_OPTIONS.filter((option) => isDocumentTypeAllowed(option.value)),
    [isDocumentTypeAllowed],
  );

  const [form, setForm] = useState(() => createEmptyForm(resolvedDefaultDocumentType));
  const [locked, setLocked] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [isNew, setIsNew] = useState(false);
  const [activeField, setActiveField] = useState(null);
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0, width: 0 });
  const [errors, setErrors] = useState({});
  const [lookingUp, setLookingUp] = useState(false);
  const [remoteClients, setRemoteClients] = useState([]);
  const [searchingClients, setSearchingClients] = useState(false);
  const [searchedQuery, setSearchedQuery] = useState('');

  const numeroRef = useRef(null);
  const nombreRef = useRef(null);
  const dropdownRef = useRef(null);
  const containerRef = useRef(null);
  const searchCacheRef = useRef(new Map());
  const searchAbortRef = useRef(null);
  const lastSyncedValueRef = useRef('');

  const notify = useCallback((nextForm, nextLocked, nextIsDirty, nextIsNew) => {
    onFormChange?.(nextForm, { isDirty: nextIsDirty, isNew: nextIsNew, id: nextLocked ? value : null });
  }, [onFormChange, value]);

  useEffect(() => {
    if (!value) return;
    if (locked && isDirty && lastSyncedValueRef.current === String(value)) return;
    const found = mergeClients(clients, remoteClients)
      .filter((client) => isDocumentTypeAllowed(client?.tipo_documento))
      .find((client) => String(client.id) === String(value));
    if (!found) return;
    const nextForm = normalizeFiscalClientForm(found);
    setForm(nextForm);
    setLocked(true);
    setIsDirty(false);
    setIsNew(false);
    setErrors({});
    lastSyncedValueRef.current = String(found.id);
    notify(nextForm, true, false, false);
  }, [value, clients, remoteClients, notify, isDocumentTypeAllowed, locked, isDirty]);

  const fillFromClient = useCallback((client) => {
    if (!isDocumentTypeAllowed(client?.tipo_documento)) return;
    const nextForm = normalizeFiscalClientForm(client);
    setRemoteClients((current) => mergeClients([client], current));
    setForm(nextForm);
    setLocked(true);
    setIsDirty(false);
    setIsNew(false);
    setActiveField(null);
    setErrors({});
    lastSyncedValueRef.current = String(client.id);
    notify(nextForm, true, false, false);
  }, [notify, isDocumentTypeAllowed]);

  const matchedClients = useCallback((query, source = clients) => {
    if (!query.trim()) return [];
    return source
      .filter((client) => isDocumentTypeAllowed(client?.tipo_documento))
      .filter((client) => clientMatchesQuery(client, query))
      .slice(0, 12);
  }, [clients, isDocumentTypeAllowed]);

  const activeQuery = activeField === 'numero' ? form.numero_documento : form.razon_social;

  useEffect(() => {
    if (!activeField || locked) {
      searchAbortRef.current?.abort();
      setRemoteClients([]);
      setSearchingClients(false);
      setSearchedQuery('');
      return undefined;
    }

    const query = String(activeQuery || '').trim();
    if (query.length < SEARCH_MIN_CHARS) {
      searchAbortRef.current?.abort();
      setRemoteClients([]);
      setSearchingClients(false);
      setSearchedQuery('');
      return undefined;
    }

    const cacheKey = query.toLowerCase();
    const cached = searchCacheRef.current.get(cacheKey);
    if (cached) {
      setRemoteClients(cached);
      setSearchingClients(false);
      setSearchedQuery(query);
      return undefined;
    }

    setRemoteClients([]);
    setSearchingClients(true);
    setSearchedQuery('');
    searchAbortRef.current?.abort();
    const controller = new AbortController();
    searchAbortRef.current = controller;

    const timerId = setTimeout(() => {
      cliSvc.search(query, SEARCH_LIMIT, { signal: controller.signal })
        .then((items) => {
          const results = Array.isArray(items) ? items : [];
          searchCacheRef.current.set(cacheKey, results);
          if (!controller.signal.aborted) {
            setRemoteClients(results);
            setSearchedQuery(query);
          }
        })
        .catch((error) => {
          if (!error?.isCanceled && !controller.signal.aborted) {
            setRemoteClients([]);
            setSearchedQuery(query);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setSearchingClients(false);
          if (searchAbortRef.current === controller) searchAbortRef.current = null;
        });
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      clearTimeout(timerId);
      controller.abort();
    };
  }, [activeField, activeQuery, locked]);

  const currentSearchQuery = String(activeQuery || '').trim();
  const remoteResultsMatchCurrentQuery = searchedQuery.trim().toLowerCase() === currentSearchQuery.toLowerCase();
  const dropdownList = activeField
    ? mergeClients(
      remoteResultsMatchCurrentQuery ? remoteClients : [],
      matchedClients(activeQuery, clients),
    )
      .filter((client) => isDocumentTypeAllowed(client?.tipo_documento))
      .slice(0, 12)
    : [];
  const canShowSearchMenu = activeField && !locked && currentSearchQuery.length >= SEARCH_MIN_CHARS;
  const showNoSearchResults = canShowSearchMenu
    && !searchingClients
    && remoteResultsMatchCurrentQuery
    && dropdownList.length === 0;

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
    const safeRawValue = key === 'tipo_documento' && !isDocumentTypeAllowed(rawValue)
      ? resolvedDefaultDocumentType
      : rawValue;
    const nextValue = key === 'telefono'
      ? safeRawValue.replace(/\D/g, '').slice(0, 9)
      : key === 'numero_documento'
        ? normalizeFiscalDocumentNumber(form.tipo_documento, safeRawValue)
        : key === 'ubigeo'
          ? normalizeFiscalUbigeo(safeRawValue)
          : normalizeUppercaseFieldValue(key, safeRawValue);

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
    const emptyForm = createEmptyForm(resolvedDefaultDocumentType);
    onChange('');
    setForm(emptyForm);
    setLocked(false);
    setIsDirty(false);
    setIsNew(false);
    setErrors({});
    setActiveField(null);
    lastSyncedValueRef.current = '';
    notify(emptyForm, false, false, false);
    setTimeout(() => numeroRef.current?.focus(), 0);
  };

  const handleLookup = async () => {
    const numero = form.numero_documento.trim();
    if (!numero) {
      validate({ ...form, numero_documento: '' });
      return;
    }

    const found = clients
      .filter((client) => isDocumentTypeAllowed(client?.tipo_documento))
      .find((client) => String(client.numero_documento || '').trim() === numero);
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
        .filter((client) => isDocumentTypeAllowed(client?.tipo_documento))
        .find((client) => String(client.numero_documento || '').trim() === numero);
      if (remoteFound) {
        handleSelectClient(remoteFound);
        return;
      }

      const data = await cliSvc.lookupDocument(numero);
      const resolvedName = getLookupName(data);
      const lookupDocumentType = getLookupDocumentType(data, form.tipo_documento);
      const nextForm = {
        ...form,
        tipo_documento: isDocumentTypeAllowed(lookupDocumentType)
          ? lookupDocumentType
          : resolvedDefaultDocumentType,
        razon_social: resolvedName || form.razon_social,
        nombre_comercial: getLookupCommercialName(data) || form.nombre_comercial,
        direccion: getLookupAddress(data) || form.direccion,
        ubigeo: normalizeFiscalUbigeo(getLookupUbigeo(data) || form.ubigeo),
      };
      setForm(nextForm);
      validate(nextForm);
      notify(nextForm, locked, isDirty, isNew);
    } catch (error) {
      setErrors((current) => ({
        ...current,
        numero_documento: error?.message || 'No se pudo consultar el documento.',
      }));
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
              aria-label="Tipo de documento"
              className="input client-combobox-input client-combobox-input--locked"
              value={getFiscalDocLabel(form.tipo_documento)}
            />
          ) : (
            <CustomSelect
              compact
              value={form.tipo_documento}
              onChange={(nextValue) => setField('tipo_documento', nextValue)}
              options={documentTypeOptions}
            />
          )}
        </div>

        <div className="field span-4">
          <label className={locked ? 'label client-combobox-label-muted' : 'label'}>
            Número doc. {!locked && <span className="req">*</span>}
          </label>
          <div className="control-with-button">
            <div className="control" style={{ flex: 1, position: 'relative' }}>
              <input
                ref={numeroRef}
                readOnly={locked}
                aria-label="Número de documento"
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
            Razón social / Nombre {!locked && <span className="req">*</span>}
          </label>
          <div className="control">
            <input
              ref={nombreRef}
              readOnly={locked}
              aria-label="Razón social o nombre"
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
            Correo electrónico
            <span className="client-combobox-label-note">(opcional)</span>
            {locked && isDirty && <span className="client-combobox-label-edit">EDITADO</span>}
          </label>
          <div className="control">
            <input
              type="email"
              aria-label="Correo electrónico"
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
            Teléfono / WhatsApp
            <span className="client-combobox-label-note">(opcional)</span>
            {locked && isDirty && <span className="client-combobox-label-edit">EDITADO</span>}
          </label>
          <div className="control">
            <input
              type="tel"
              aria-label="Teléfono o WhatsApp"
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
            Dirección fiscal
            <span className="client-combobox-label-note">
              {form.tipo_documento === '6' ? '(obligatoria para factura)' : '(opcional)'}
            </span>
            {locked && isDirty && <span className="client-combobox-label-edit">EDITADO</span>}
          </label>
          <div className="control">
            <input
              aria-label="Dirección fiscal"
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
              aria-label="Ubigeo"
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
          Los cambios en correo, teléfono, dirección o ubigeo <strong>actualizarán al cliente</strong> en el catálogo al guardar.
        </p>
      )}
      {hasNewData && !locked && (
        <p className="client-combobox-status client-combobox-status--new" style={{ marginTop: '10px' }}>
          Nuevo cliente — <span className="font-semibold text-[var(--color-primary)]">se registrará al guardar la cotización</span>.
        </p>
      )}

      {errors._ && <p className="client-combobox-error mb-1">{errors._}</p>}

      {canShowSearchMenu && createPortal(
        <div
          ref={dropdownRef}
          className="ink-combobox-menu dropdown-enter"
          style={{
            top: dropdownPos.top,
            left: dropdownPos.left,
            width: Math.max(dropdownPos.width, 320),
          }}
        >
          {searchingClients && (
            <div className="ink-combobox-feedback">
              <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
              Buscando clientes...
            </div>
          )}
          {showNoSearchResults && (
            <div className="ink-combobox-feedback ink-combobox-feedback--empty">
              No hay clientes registrados con ese documento o nombre.
            </div>
          )}
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
