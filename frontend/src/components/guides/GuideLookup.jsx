import { cloneElement, useEffect, useId, useRef, useState } from 'react';
import './guideFormFeedback.css';
import { LoaderCircle, Search } from 'lucide-react';
import { clientes } from '../../services/clientes';
import { guias } from '../../services/guias';

const normalize = (kind, value) => kind === 'placa'
  ? String(value || '').trim().toUpperCase().replaceAll('-', '') : String(value || '').trim();

/** One input and its explicit action; feedback stays outside the input row. */
export function GuideQueryControl({ kind, children, busy, disabled, onQuery, message, error, hint, alertOnError = false }) {
  const statusId = useId();
  const description = [children.props['aria-describedby'], statusId].filter(Boolean).join(' ');
  return <div className="guide-lookup">
    <div className="guide-query-control">
      {cloneElement(children, { 'aria-describedby': description })}
      <button type="button" className="btn-secondary guide-query-button" aria-label={`Consultar ${kind}`}
        aria-busy={busy || undefined} disabled={disabled || busy} onClick={onQuery}>
        {busy ? <LoaderCircle size={14} aria-hidden="true" className="motion-safe:animate-spin" /> : <Search size={14} aria-hidden="true" />}<span>Consultar</span>
      </button>
    </div>
    {hint && <p className="guide-field-hint">{hint}</p>}
    <p id={statusId} role={error && alertOnError ? 'alert' : 'status'} className={error ? 'guide-field-error' : 'guide-field-hint'}>{message}</p>
  </div>;
}

/** Explicit, optional queries. Late results never replace another identity or manual edits. */
export default function GuideLookup({ kind, form, setForm, source, targets = {}, identityType, onApplied, children }) {
  const latest = useRef(form);
  latest.current = form;
  const sequence = useRef(0);
  const [state, setState] = useState({ busy: false, message: '', error: false });
  const number = normalize(kind, form[source]);
  const identity = `${kind}:${number}:${identityType || ''}`;
  const latestIdentity = useRef(identity);
  latestIdentity.current = identity;
  const valid = kind === 'placa' ? /^[A-Z0-9]{5,8}$/.test(number)
    : kind === 'RUC' ? /^[0-9]{11}$/.test(number) : /^[0-9]{8}$/.test(number);
  useEffect(() => {
    setState({ busy: false, message: '', error: false });
    return () => { sequence.current += 1; };
  }, [identity]);

  const query = async () => {
    if (!valid || state.busy) return;
    const ticket = ++sequence.current;
    const before = latest.current;
    setState({ busy: true, message: `Consultando ${kind}…`, error: false });
    try {
      const data = kind === 'placa' ? await guias.lookupPlate(number)
        : kind === 'licencia' ? await guias.lookupLicense(number) : await clientes.lookupDocument(number);
      if (ticket !== sequence.current || latestIdentity.current !== identity) return;
      const returnedNumber = kind === 'placa' ? data.placa : data.documento;
      if (normalize(kind, returnedNumber) !== number) throw new Error('La respuesta no corresponde al dato consultado. Puedes completarlo manualmente.');
      const values = kind === 'DNI' ? {
        nombres: data.nombres, apellidos: [data.apellido_paterno, data.apellido_materno].filter(Boolean).join(' '),
      } : data;
      const patch = Object.fromEntries(Object.entries(targets).map(([target, key]) => [target, values[key]]));
      if (Object.values(patch).some((value) => !value || typeof value !== 'string')) throw new Error('La consulta devolvió datos incompletos. Puedes ingresarlos manualmente.');
      if (Object.keys(patch).some((key) => latest.current[key] !== before[key])) throw new Error('Cambiaste los datos durante la consulta. Conservamos tus cambios; puedes consultar otra vez.');
      setForm((current) => normalize(kind, current[source]) === number && Object.keys(patch).every((key) => current[key] === before[key]) ? { ...current, ...patch } : current);
      onApplied?.(Object.keys(patch));
      const detail = kind === 'placa' ? [data.marca, data.modelo, data.color].filter(Boolean).join(' · ')
        : kind === 'licencia' ? [data.categoria, data.estado, data.fecha_vencimiento && `Vence: ${data.fecha_vencimiento}`].filter(Boolean).join(' · ')
          : 'Datos completados. Revísalos antes de continuar.';
      setState({ busy: false, error: false, message: detail || 'Consulta completada. Revisa los datos.' });
    } catch (error) {
      if (ticket === sequence.current && latestIdentity.current === identity)
        setState({ busy: false, error: true, message: `${error.message || 'No se pudo consultar.'} Puedes ingresar los datos manualmente.` });
    }
  };

  return <GuideQueryControl kind={kind} busy={state.busy} disabled={!valid} onQuery={query}
    message={state.message} error={state.error}
    hint={kind === 'licencia' && !number ? 'Ingresa primero el DNI del conductor.' : undefined}>
    {children}
  </GuideQueryControl>;
}
