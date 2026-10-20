import { cloneElement, createContext, isValidElement, useContext, useEffect, useId, useRef, useState } from 'react';
import './guideFormFeedback.css';

const FeedbackContext = createContext(null);

function nativeMessage(control) {
  if (control.validity.valueMissing) return 'Completa este campo.';
  if (control.validity.rangeUnderflow) return `El valor mínimo es ${control.min}.`;
  if (control.validity.rangeOverflow) return `El valor máximo es ${control.max}.`;
  if (control.validity.stepMismatch) return 'Revisa los decimales permitidos para esta cantidad.';
  if (control.validity.patternMismatch) return 'Revisa el formato indicado para este dato.';
  return 'Revisa el valor de este campo.';
}

export function useGuideFormFeedback({ onFieldFocus } = {}) {
  const prefix = useId();
  const formRef = useRef(null);
  const summaryRef = useRef(null);
  const [feedback, setFeedback] = useState({ message: '', errors: {} });
  const [focusRequest, setFocusRequest] = useState(0);
  useEffect(() => {
    if (focusRequest) summaryRef.current?.focus();
  }, [focusRequest]);

  const show = (errors, message = 'Revisa los campos indicados antes de guardar.') => {
    setFeedback({ errors, message });
    setFocusRequest((value) => value + 1);
  };
  const control = (name) => ({
    id: `${prefix}-${name}`, name,
    'aria-invalid': Boolean(feedback.errors[name]),
    'aria-describedby': feedback.errors[name] ? `${prefix}-${name}-error` : undefined,
  });
  const fieldElement = (name) => document.getElementById(`${prefix}-${name}-field`);
  const focusField = (name) => {
    onFieldFocus?.(name);
    requestAnimationFrame(() => (formRef.current?.elements.namedItem(name) || fieldElement(name)?.querySelector('input, button, select, textarea'))?.focus());
  };
  const clearField = (name) => setFeedback((current) => {
    if (!current.errors[name]) return current;
    const errors = { ...current.errors };
    delete errors[name];
    return { errors, message: Object.keys(errors).length ? current.message : '' };
  });
  const validate = (form, includeHidden = false) => {
    const errors = {};
    for (const input of form.elements) {
      if (input.name && input.willValidate && (includeHidden || !input.closest('[hidden]')) && !input.validity.valid) errors[input.name] = nativeMessage(input);
    }
    if (Object.keys(errors).length) { show(errors); return false; }
    setFeedback({ errors: {}, message: '' });
    return true;
  };
  const reportError = (error, aliases = {}) => {
    const detail = error.detail;
    const issues = Array.isArray(detail) ? detail : detail?.errors || [];
    const errors = {};
    for (const issue of Array.isArray(issues) ? issues : []) {
      if (!issue || typeof issue !== 'object') continue;
      const path = typeof issue.field === 'string' ? issue.field : Array.isArray(issue.loc) ? issue.loc.filter((part) => part !== 'body').join('.') : undefined;
      const name = aliases[path] || path;
      if (!name || (!formRef.current?.elements.namedItem(name) && !fieldElement(name))) continue;
      errors[name] = typeof issue.message === 'string' ? issue.message : issue.type === 'missing' ? 'Completa este campo.' : 'Revisa este dato y vuelve a guardar.';
    }
    const inconclusive = error.isTimeout || error.status == null;
    const message = inconclusive
      ? 'No recibimos confirmación del guardado. Revisa la bandeja de guías antes de volver a guardar.'
      : error.message || 'No se pudo completar el guardado. Inténtalo nuevamente.';
    show(errors, Object.keys(errors).length ? undefined : message);
  };
  return { ...feedback, formRef, summaryRef, control, show, reportError, focusField, clearField, validate, reset: () => setFeedback({ errors: {}, message: '' }) };
}

export function GuideForm({ feedback, children, onSubmit, validateHidden = false, ...props }) {
  return <FeedbackContext.Provider value={feedback}>
    <form {...props} ref={feedback.formRef} noValidate onChangeCapture={(event) => feedback.clearField(event.target.name)} onSubmit={(event) => {
      event.preventDefault();
      if (feedback.validate(event.currentTarget, validateHidden)) onSubmit(event);
    }}>{children}</form>
  </FeedbackContext.Provider>;
}

export function GuideFormErrors() {
  const feedback = useContext(FeedbackContext);
  if (!feedback.message) return null;
  return <div className="guide-form-feedback" role="alert" tabIndex={-1} ref={feedback.summaryRef}>
    <strong>Revisa la guía</strong>
    <p>{feedback.message}</p>
    {Object.entries(feedback.errors).map(([name, message]) => <p key={name}>
      <button type="button" onClick={() => feedback.focusField(name)}>{feedback.formRef.current?.elements.namedItem(name)?.getAttribute('data-field-label') || document.getElementById(`${feedback.control(name).id}-label`)?.textContent || 'Ir al campo'}: {message}</button>
    </p>)}
  </div>;
}

export function GuideField({ name, label, children, hint, required, icon: Icon, className = '', lookup }) {
  const feedback = useContext(FeedbackContext);
  const localId = useId();
  const fieldName = name || children?.props?.name || localId;
  const id = feedback.control(fieldName).id;
  const error = feedback.errors[fieldName];
  const description = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined;
  const native = isValidElement(children) && ['input', 'select', 'textarea'].includes(children.type);
  const containsNamedInput = children?.type === 'div' && Boolean(name);
  const Label = native || containsNamedInput ? 'label' : 'span';
  const enhanced = native ? cloneElement(children, {
    ...children.props, ...feedback.control(fieldName),
    'aria-describedby': description, 'data-field-label': label,
  }) : children;
  return <div id={`${id}-field`} className={`guide-accessible-field flex flex-col gap-1.5 ${className}`.trim()} role="group" aria-labelledby={`${id}-label`} aria-describedby={description}>
    <div className="flex items-center gap-1.5 text-xs font-bold text-[var(--color-text)]">
      <Label id={`${id}-label`} htmlFor={native || containsNamedInput ? id : undefined} className="flex items-center gap-1.5">
        {Icon && <Icon size={16} aria-hidden="true" />}{label}
      </Label>
      {required && <span aria-hidden="true">*</span>}
    </div>
    {lookup ? cloneElement(lookup, { children: enhanced }) : enhanced}
    {hint && <p id={`${id}-hint`} className="guide-field-hint">{hint}</p>}
    {error && <p id={`${id}-error`} className="guide-field-error">{error}</p>}
  </div>;
}
