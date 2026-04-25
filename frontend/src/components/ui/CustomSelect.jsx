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
  const [dropPos, setDropPos] = useState({ top: 0, left: 0, width: 0, maxHeight: 260 });
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

  const syncDropdownPosition = () => {
    const trigger = triggerRef.current;
    if (!trigger || typeof window === 'undefined') return;

    const rect = trigger.getBoundingClientRect();
    const viewportPadding = 12;
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    const dropdownWidth = Math.min(
      Math.max(rect.width, compact ? 220 : rect.width),
      window.innerWidth - viewportPadding * 2,
    );
    const measuredHeight = dropdownRef.current?.offsetHeight || 260;
    const spaceBelow = window.innerHeight - rect.bottom - viewportPadding;
    const spaceAbove = rect.top - viewportPadding;
    const placeAbove = spaceBelow < Math.min(measuredHeight, 260) && spaceAbove > spaceBelow;
    const availableHeight = Math.max(160, placeAbove ? spaceAbove : spaceBelow);
    const renderedHeight = Math.min(measuredHeight, availableHeight);
    const minLeft = scrollX + viewportPadding;
    const maxLeft = scrollX + window.innerWidth - viewportPadding - dropdownWidth;
    const left = Math.min(Math.max(rect.left + scrollX, minLeft), Math.max(minLeft, maxLeft));

    setDropPos({
      top: placeAbove
        ? rect.top + scrollY - renderedHeight - 6
        : rect.bottom + scrollY + 6,
      left,
      width: dropdownWidth,
      maxHeight: availableHeight,
    });
  };

  const openDropdown = () => {
    if (disabled) return;
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
    const handleViewport = () => syncDropdownPosition();
    syncDropdownPosition();
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKey);
    window.addEventListener('resize', handleViewport);
    window.addEventListener('scroll', handleViewport, true);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKey);
      window.removeEventListener('resize', handleViewport);
      window.removeEventListener('scroll', handleViewport, true);
    };
  }, [open, compact, filteredOptions.length, showCreateOption]);

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
      className={`ink-chevron ${open ? 'is-open' : ''}`}
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
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
        className={`ink-select-trigger ${compact ? 'ink-select-trigger--compact' : ''} ${open ? 'is-open' : ''}`}
      >
        <div className={`ink-select-value ${selected ? '' : 'text-[var(--text-tertiary)]'}`}>
          {selected ? (
            renderPreview ? renderPreview(selected) : (
              <span>{selected.label}</span>
            )
          ) : (
            <span>{placeholder}</span>
          )}
        </div>
        {chevron}
      </button>

      {open && createPortal(
        <div
          ref={dropdownRef}
          className="ink-select-dropdown"
          style={{
            top: dropPos.top,
            left: dropPos.left,
            width: dropPos.width,
            maxHeight: dropPos.maxHeight,
          }}
        >
          {searchable && (
            <div className="ink-select-search">
              <input
                ref={searchInputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={searchPlaceholder}
                className="input-flat w-full text-xs"
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
                className={`ink-select-option ${isActive ? 'is-active' : ''}`}
              >
                {renderOption ? (
                  renderOption(opt, { isActive, query: normalizedQuery })
                ) : (
                  <>
                    {isActive ? (
                      <svg
                        className="h-3 w-3 shrink-0"
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : (
                      <span className="w-3 shrink-0" />
                    )}
                    {opt.label}
                  </>
                )}
              </div>
            );
          })}

          {!filteredOptions.length && !showCreateOption && (
            <div className="ink-select-option-empty">
              {noResultsLabel}
            </div>
          )}

          {showCreateOption && (
            <div
              onMouseDown={(e) => {
                e.preventDefault();
                handleCreate();
              }}
              className="ink-select-option-action"
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
              className="ink-select-option-action"
            >
              {footerAction.label}
            </div>
          )}
        </div>,
        document.body,
      )}
    </>
  );
}
