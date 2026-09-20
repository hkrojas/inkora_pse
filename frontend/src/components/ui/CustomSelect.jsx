import { useState, useRef, useEffect, useId } from 'react';
import { createPortal } from 'react-dom';

export default function CustomSelect({
  id,
  value,
  onChange,
  options = [],
  placeholder = 'Seleccionar...',
  disabled = false,
  compact = false,
  searchable = false,
  searchPlaceholder = 'Buscar...',
  onSearchChange,
  loading = false,
  filterOption,
  renderOption,
  renderPreview,
  onCreateNew,
  createLabel,
  matchOption,
  noResultsLabel = 'Sin resultados',
  footerAction,
  ariaLabel,
  ariaLabelledby,
  required = false,
  className = '',
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [dropPos, setDropPos] = useState({ top: 0, left: 0, width: 0, maxHeight: 260 });
  const triggerRef = useRef(null);
  const dropdownRef = useRef(null);
  const searchInputRef = useRef(null);
  const selectedOptionRef = useRef(null);
  const generatedId = useId().replace(/:/g, '');
  const triggerId = id || `ink-select-${generatedId}`;
  const listboxId = `${triggerId}-listbox`;

  const selectedFromOptions = options.find((opt) => String(opt.value) === String(value));
  if (selectedFromOptions) selectedOptionRef.current = selectedFromOptions;
  const selected = selectedFromOptions || (
    String(selectedOptionRef.current?.value) === String(value) ? selectedOptionRef.current : undefined
  );
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
    const selectedIndex = filteredOptions.findIndex((opt) => String(opt.value) === String(value));
    setHighlightedIndex(selectedIndex >= 0 ? selectedIndex : 0);
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e) => {
      const insideTrigger = triggerRef.current?.contains(e.target);
      const insideDropdown = dropdownRef.current?.contains(e.target);
      if (!insideTrigger && !insideDropdown) setOpen(false);
    };
    const handleKey = (e) => {
      if (e.key === 'Escape') {
        setOpen(false);
        triggerRef.current?.focus();
        return;
      }
      if (!['ArrowDown', 'ArrowUp', 'Enter'].includes(e.key) || !filteredOptions.length) return;
      e.preventDefault();
      if (e.key === 'ArrowDown') {
        setHighlightedIndex((current) => (current + 1 + filteredOptions.length) % filteredOptions.length);
      } else if (e.key === 'ArrowUp') {
        setHighlightedIndex((current) => (current - 1 + filteredOptions.length) % filteredOptions.length);
      } else if (filteredOptions[highlightedIndex]) {
        handleSelect(filteredOptions[highlightedIndex].value);
        triggerRef.current?.focus();
      }
    };
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
  }, [open, compact, filteredOptions.length, highlightedIndex, showCreateOption]);

  useEffect(() => {
    if (!open) {
      setQuery('');
      setHighlightedIndex(-1);
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
        id={triggerId}
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={open ? () => setOpen(false) : openDropdown}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledby}
        aria-required={required || undefined}
        aria-activedescendant={open && filteredOptions[highlightedIndex] ? `${listboxId}-option-${highlightedIndex}` : undefined}
        onKeyDown={(event) => {
          if (!open && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
            event.preventDefault();
            openDropdown();
          }
        }}
        className={`ink-select-trigger ${compact ? 'ink-select-trigger--compact' : ''} ${open ? 'is-open' : ''} ${className}`}
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
          id={listboxId}
          ref={dropdownRef}
          className="ink-select-dropdown dropdown-enter"
          role="listbox"
          aria-label={ariaLabel || 'Opciones'}
          aria-busy={loading || undefined}
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
                onChange={(e) => {
                  setQuery(e.target.value);
                  setHighlightedIndex(0);
                  onSearchChange?.(e.target.value);
                }}
                placeholder={searchPlaceholder}
                aria-label={searchPlaceholder}
                className="input-flat w-full text-xs"
                onMouseDown={(e) => e.stopPropagation()}
              />
            </div>
          )}

          {filteredOptions.map((opt, index) => {
            const isActive = String(opt.value) === String(value);
            return (
              <div
                id={`${listboxId}-option-${index}`}
                key={opt.value}
                onMouseDown={(e) => { e.preventDefault(); handleSelect(opt.value); }}
                onMouseEnter={() => setHighlightedIndex(index)}
                className={`ink-select-option ${isActive ? 'is-active' : ''} ${highlightedIndex === index ? 'is-highlighted' : ''}`}
                role="option"
                aria-selected={isActive}
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

          {loading && (
            <div className="ink-select-option-empty" role="status" aria-live="polite">Buscando resultados…</div>
          )}
          {!loading && !filteredOptions.length && !showCreateOption && (
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
