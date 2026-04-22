import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';

export default function CustomSelect({
  value,
  onChange,
  options = [],
  placeholder = 'Seleccionar...',
  disabled = false,
  compact = false,
  searchable = false,
  searchPlaceholder = 'Buscar...',
  filterOption,
  renderOption,
  renderPreview,
  onCreateNew,
  createLabel,
  matchOption,
  noResultsLabel = 'Sin resultados',
  footerAction,
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [dropPos, setDropPos] = useState({ top: 0, left: 0, width: 0 });
  const triggerRef = useRef(null);
  const dropdownRef = useRef(null);
  const searchInputRef = useRef(null);

  const selected = options.find((opt) => String(opt.value) === String(value));
  const normalizedQuery = query.trim().toLowerCase();
  const filteredOptions = searchable
    ? options.filter((opt) => {
        if (!normalizedQuery) return true;
        if (typeof filterOption === 'function') {
          return filterOption(opt, normalizedQuery);
        }
        return String(opt.searchText || opt.label || '')
          .toLowerCase()
          .includes(normalizedQuery);
      })
    : options;
  const hasExactMatch = searchable && normalizedQuery
    ? options.some((opt) => {
        if (typeof matchOption === 'function') {
          return matchOption(opt, normalizedQuery);
        }
        return String(opt.label || '').trim().toLowerCase() === normalizedQuery;
      })
    : false;
  const showCreateOption = Boolean(
    searchable && onCreateNew && normalizedQuery && !hasExactMatch,
  );

  const openDropdown = () => {
    if (disabled) return;
    const rect = triggerRef.current.getBoundingClientRect();
    setDropPos({
      top: rect.bottom + window.scrollY,
      left: rect.left + window.scrollX,
      width: rect.width,
    });
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e) => {
      const insideTrigger = triggerRef.current?.contains(e.target);
      const insideDropdown = dropdownRef.current?.contains(e.target);
      if (!insideTrigger && !insideDropdown) setOpen(false);
    };
    const handleKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  useEffect(() => {
    if (!open) {
      setQuery('');
      return;
    }
    if (searchable) {
      window.setTimeout(() => searchInputRef.current?.focus(), 0);
    }
  }, [open, searchable]);

  const handleSelect = (optValue) => {
    onChange(optValue);
    setOpen(false);
    setQuery('');
  };

  const handleCreate = () => {
    const text = query.trim();
    if (!text || !onCreateNew) return;
    onCreateNew(text);
    setOpen(false);
    setQuery('');
  };

  const chevron = (
    <svg
      width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke={open ? '#4F46E5' : '#94A3B8'} strokeWidth="2.5"
      strokeLinecap="round" strokeLinejoin="round"
      style={{ flexShrink: 0, transition: 'transform 150ms', transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={open ? () => setOpen(false) : openDropdown}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          width: '100%',
          minHeight: compact ? '40px' : '44px',
          padding: compact ? '8px 10px 8px 12px' : '10px 12px 10px 14px',
          background: open ? '#ffffff' : '#F8FAFC',
          border: open ? '1.5px solid #4F46E5' : '1.5px solid #E2E8F0',
          borderRadius: 0,
          boxShadow: open ? 'inset 0 0 0 1px #4F46E5' : 'none',
          color: selected ? 'var(--text-primary)' : '#94A3B8',
          fontSize: '14px',
          fontFamily: 'var(--font-body)',
          fontWeight: selected ? 500 : 400,
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          transition: 'border-color 150ms, box-shadow 150ms, background 150ms',
          textAlign: 'left',
        }}
        onMouseEnter={(e) => { if (!open && !disabled) e.currentTarget.style.borderColor = '#94A3B8'; }}
        onMouseLeave={(e) => { if (!open && !disabled) e.currentTarget.style.borderColor = open ? '#4F46E5' : '#E2E8F0'; }}
      >
        <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
          {selected ? (
            renderPreview ? renderPreview(selected) : (
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}>
                {selected.label}
              </span>
            )
          ) : (
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}>
              {placeholder}
            </span>
          )}
        </div>
        {chevron}
      </button>

      {open && createPortal(
        <div
          ref={dropdownRef}
          style={{
            position: 'absolute',
            top: dropPos.top,
            left: dropPos.left,
            width: dropPos.width,
            zIndex: 99999,
            background: '#ffffff',
            border: '1.5px solid #4F46E5',
            borderTop: 'none',
            boxShadow: '4px 4px 0px 0px rgba(99,102,241,0.35)',
            maxHeight: '260px',
            overflowY: 'auto',
          }}
        >
          {searchable && (
            <div style={{ position: 'sticky', top: 0, zIndex: 1, background: '#ffffff', borderBottom: '1px solid #E2E8F0', padding: '10px 12px' }}>
              <input
                ref={searchInputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={searchPlaceholder}
                className="input-flat"
                style={{ width: '100%', fontSize: '13px' }}
                onMouseDown={(e) => e.stopPropagation()}
              />
            </div>
          )}

          {filteredOptions.map((opt) => {
            const isActive = String(opt.value) === String(value);
            return (
              <div
                key={opt.value}
                onMouseDown={(e) => { e.preventDefault(); handleSelect(opt.value); }}
                style={{
                  padding: '10px 14px',
                  fontSize: '13px',
                  fontFamily: 'var(--font-body)',
                  fontWeight: isActive ? 700 : 400,
                  color: isActive ? '#4F46E5' : '#0F172A',
                  background: isActive ? '#EEF2FF' : 'transparent',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  borderLeft: isActive ? '3px solid #4F46E5' : '3px solid transparent',
                  userSelect: 'none',
                }}
                onMouseEnter={(e) => { if (!isActive) { e.currentTarget.style.background = '#F8FAFC'; e.currentTarget.style.borderLeftColor = '#C7D2FE'; }}}
                onMouseLeave={(e) => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderLeftColor = 'transparent'; }}}
              >
                {renderOption ? (
                  renderOption(opt, { isActive, query: normalizedQuery })
                ) : (
                  <>
                    {isActive
                      ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><polyline points="20 6 9 17 4 12" /></svg>
                      : <span style={{ width: '12px', flexShrink: 0 }} />
                    }
                    {opt.label}
                  </>
                )}
              </div>
            );
          })}

          {!filteredOptions.length && !showCreateOption && (
            <div style={{ padding: '12px 14px', fontSize: '12px', color: '#94A3B8' }}>
              {noResultsLabel}
            </div>
          )}

          {showCreateOption && (
            <div
              onMouseDown={(e) => {
                e.preventDefault();
                handleCreate();
              }}
              style={{
                padding: '10px 14px',
                fontSize: '13px',
                fontFamily: 'var(--font-body)',
                fontWeight: 700,
                color: '#4F46E5',
                background: '#EEF2FF',
                cursor: 'pointer',
                borderTop: '1px solid #E2E8F0',
                userSelect: 'none',
              }}
            >
              {typeof createLabel === 'function'
                ? createLabel(query.trim())
                : (createLabel || `+ Crear: ${query.trim()}`)}
            </div>
          )}

          {footerAction && (
            <div
              onMouseDown={(e) => {
                e.preventDefault();
                footerAction.onClick?.();
                setOpen(false);
                setQuery('');
              }}
              style={{
                padding: '10px 14px',
                fontSize: '13px',
                fontFamily: 'var(--font-body)',
                fontWeight: 700,
                color: '#4F46E5',
                background: '#ffffff',
                cursor: 'pointer',
                borderTop: '1px solid #E2E8F0',
                userSelect: 'none',
              }}
            >
              {footerAction.label}
            </div>
          )}
        </div>,
        document.body
      )}
    </>
  );
}
