import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Pipette } from 'lucide-react';

const HEX_COLOR_PATTERN = /^#([0-9A-F]{6})$/i;

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function sanitizeHexCandidate(value) {
  const rawValue = String(value || '').trim().toUpperCase();
  if (!rawValue) return '';
  return rawValue.startsWith('#') ? rawValue : `#${rawValue}`;
}

function normalizeHex(value, fallback = '#2563EB') {
  const candidate = sanitizeHexCandidate(value);
  if (HEX_COLOR_PATTERN.test(candidate)) return candidate;
  return sanitizeHexCandidate(fallback || '#2563EB') || '#2563EB';
}

function hexToRgb(hex) {
  const normalized = normalizeHex(hex);
  return {
    r: Number.parseInt(normalized.slice(1, 3), 16),
    g: Number.parseInt(normalized.slice(3, 5), 16),
    b: Number.parseInt(normalized.slice(5, 7), 16),
  };
}

function channelToHex(value) {
  return clamp(Math.round(value), 0, 255).toString(16).padStart(2, '0').toUpperCase();
}

function rgbToHex({ r, g, b }) {
  return `#${channelToHex(r)}${channelToHex(g)}${channelToHex(b)}`;
}

function rgbToHsl({ r, g, b }) {
  const rNorm = clamp(r, 0, 255) / 255;
  const gNorm = clamp(g, 0, 255) / 255;
  const bNorm = clamp(b, 0, 255) / 255;
  const max = Math.max(rNorm, gNorm, bNorm);
  const min = Math.min(rNorm, gNorm, bNorm);
  const delta = max - min;
  const lightness = (max + min) / 2;

  if (delta === 0) {
    return { h: 0, s: 0, l: lightness * 100 };
  }

  const saturation = delta / (1 - Math.abs(2 * lightness - 1));
  let hue = 0;

  switch (max) {
    case rNorm:
      hue = 60 * (((gNorm - bNorm) / delta) % 6);
      break;
    case gNorm:
      hue = 60 * ((bNorm - rNorm) / delta + 2);
      break;
    default:
      hue = 60 * ((rNorm - gNorm) / delta + 4);
      break;
  }

  return {
    h: (hue + 360) % 360,
    s: saturation * 100,
    l: lightness * 100,
  };
}

function hslToRgb({ h, s, l }) {
  const hue = ((Number(h) % 360) + 360) % 360;
  const saturation = clamp(Number(s), 0, 100) / 100;
  const lightness = clamp(Number(l), 0, 100) / 100;
  const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
  const segment = hue / 60;
  const second = chroma * (1 - Math.abs((segment % 2) - 1));
  const match = lightness - chroma / 2;

  let red = 0;
  let green = 0;
  let blue = 0;

  if (segment >= 0 && segment < 1) {
    red = chroma;
    green = second;
  } else if (segment < 2) {
    red = second;
    green = chroma;
  } else if (segment < 3) {
    green = chroma;
    blue = second;
  } else if (segment < 4) {
    green = second;
    blue = chroma;
  } else if (segment < 5) {
    red = second;
    blue = chroma;
  } else {
    red = chroma;
    blue = second;
  }

  return {
    r: Math.round((red + match) * 255),
    g: Math.round((green + match) * 255),
    b: Math.round((blue + match) * 255),
  };
}

function hexToRgba(hex, alpha) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function ColorRange({ label, value, min, max, onChange, background }) {
  return (
    <label className="pdf-color-picker-slider">
      <span className="pdf-color-picker-slider-label">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="pdf-color-picker-range"
        style={{ background }}
      />
      <span className="pdf-color-picker-slider-value">{Math.round(value)}</span>
    </label>
  );
}

export default function ColorPickerField({
  label,
  value,
  onChange,
  fallback = '#2563EB',
  presets = [],
  openUpward = false,
}) {
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const popoverRef = useRef(null);
  const safeValue = normalizeHex(value, fallback);
  const [isOpen, setIsOpen] = useState(false);
  const [popoverPos, setPopoverPos] = useState({ top: 0, left: 0, width: 0, maxHeight: 420 });
  const [hexInput, setHexInput] = useState(safeValue);
  const rgb = useMemo(() => hexToRgb(safeValue), [safeValue]);
  const hsl = useMemo(() => rgbToHsl(rgb), [rgb]);

  useEffect(() => {
    setHexInput(safeValue);
  }, [safeValue]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const syncPopoverPosition = () => {
      const trigger = triggerRef.current;
      if (!trigger || typeof window === 'undefined') return;

      const rect = trigger.getBoundingClientRect();
      const viewportPadding = 12;
      const scrollX = window.scrollX;
      const scrollY = window.scrollY;
      const popoverWidth = Math.min(
        Math.max(rect.width, 316),
        window.innerWidth - viewportPadding * 2,
      );
      const measuredHeight = popoverRef.current?.offsetHeight || 388;
      const spaceBelow = window.innerHeight - rect.bottom - viewportPadding;
      const spaceAbove = rect.top - viewportPadding;
      let placeAbove = Boolean(openUpward);

      if (!openUpward && spaceBelow < Math.min(measuredHeight, 388) && spaceAbove > spaceBelow) {
        placeAbove = true;
      } else if (openUpward && spaceAbove < Math.min(measuredHeight, 388) && spaceBelow > spaceAbove) {
        placeAbove = false;
      }

      const availableHeight = Math.max(220, placeAbove ? spaceAbove : spaceBelow);
      const renderedHeight = Math.min(measuredHeight, availableHeight);
      const minLeft = scrollX + viewportPadding;
      const maxLeft = scrollX + window.innerWidth - viewportPadding - popoverWidth;
      const left = Math.min(Math.max(rect.left + scrollX, minLeft), Math.max(minLeft, maxLeft));

      setPopoverPos({
        top: placeAbove
          ? rect.top + scrollY - renderedHeight - 8
          : rect.bottom + scrollY + 8,
        left,
        width: popoverWidth,
        maxHeight: availableHeight,
      });
    };

    syncPopoverPosition();

    const handlePointerDown = (event) => {
      const inRoot = rootRef.current && rootRef.current.contains(event.target);
      const inPopover = popoverRef.current && popoverRef.current.contains(event.target);
      if (!inRoot && !inPopover) {
        setIsOpen(false);
      }
    };

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    const handleViewport = () => syncPopoverPosition();

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);
    window.addEventListener('resize', handleViewport);
    window.addEventListener('scroll', handleViewport, true);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
      window.removeEventListener('resize', handleViewport);
      window.removeEventListener('scroll', handleViewport, true);
    };
  }, [isOpen, openUpward]);

  const commitHex = (nextHex) => {
    const normalized = normalizeHex(nextHex, fallback);
    setHexInput(normalized);
    onChange(normalized);
  };

  const handleHexInputChange = (event) => {
    const nextValue = sanitizeHexCandidate(event.target.value);
    setHexInput(nextValue);
    if (HEX_COLOR_PATTERN.test(nextValue)) {
      onChange(nextValue);
    }
  };

  const handleHexBlur = () => {
    commitHex(hexInput);
  };

  const commitRgb = (partialRgb) => {
    const nextRgb = {
      r: clamp(partialRgb.r ?? rgb.r, 0, 255),
      g: clamp(partialRgb.g ?? rgb.g, 0, 255),
      b: clamp(partialRgb.b ?? rgb.b, 0, 255),
    };
    commitHex(rgbToHex(nextRgb));
  };

  const commitHsl = (partialHsl) => {
    const nextHsl = {
      h: partialHsl.h ?? hsl.h,
      s: partialHsl.s ?? hsl.s,
      l: partialHsl.l ?? hsl.l,
    };
    commitHex(rgbToHex(hslToRgb(nextHsl)));
  };

  const displayPresets = presets.length > 0 ? presets : [fallback, '#0F172A', '#2563EB', '#14B8A6', '#F97316', '#EF4444'];
  const saturationBackground = `linear-gradient(90deg, hsl(${Math.round(hsl.h)}deg 0% ${Math.round(hsl.l)}%), hsl(${Math.round(hsl.h)}deg 100% ${Math.round(hsl.l)}%))`;
  const lightnessBackground = `linear-gradient(90deg, hsl(${Math.round(hsl.h)}deg ${Math.round(hsl.s)}% 0%), hsl(${Math.round(hsl.h)}deg ${Math.round(hsl.s)}% 50%), hsl(${Math.round(hsl.h)}deg ${Math.round(hsl.s)}% 100%))`;
  const previewBackground = `linear-gradient(135deg, ${hexToRgba(safeValue, 0.22)} 0%, ${hexToRgba(safeValue, 0.92)} 100%)`;

  return (
    <div ref={rootRef} className={`pdf-color-picker ${isOpen ? 'is-open' : ''}`}>
      <label className="label">{label}</label>

      <div className="pdf-color-picker-control">
        <button
          ref={triggerRef}
          type="button"
          className="pdf-color-picker-trigger"
          onClick={() => setIsOpen((current) => !current)}
          aria-expanded={isOpen}
        >
          <span className="pdf-color-picker-swatch" style={{ '--picker-color': safeValue }} />
          <span className="pdf-color-picker-meta">
            <span className="pdf-color-picker-value">{safeValue}</span>
            <span className="pdf-color-picker-hint">Abrir selector</span>
          </span>
          <ChevronDown size={16} className="pdf-color-picker-chevron" />
        </button>

        <input
          className="input pdf-color-picker-hex-input"
          value={hexInput}
          onChange={handleHexInputChange}
          onBlur={handleHexBlur}
          maxLength={7}
          spellCheck={false}
          autoComplete="off"
          placeholder="#2563EB"
        />
      </div>

      {isOpen && createPortal(
        <div
          ref={popoverRef}
          className="pdf-color-picker-popover"
          style={{
            top: popoverPos.top,
            left: popoverPos.left,
            width: popoverPos.width,
            maxHeight: popoverPos.maxHeight,
            zIndex: 9999,
          }}
        >
          <div className="pdf-color-picker-preview" style={{ background: previewBackground }}>
            <div className="pdf-color-picker-preview-chip" style={{ '--picker-color': safeValue }} />
            <div className="pdf-color-picker-preview-copy">
              <div className="pdf-color-picker-preview-title">Color activo</div>
              <div className="pdf-color-picker-preview-value">{safeValue}</div>
            </div>
            <div className="pdf-color-picker-preview-icon">
              <Pipette size={16} />
            </div>
          </div>

          <div className="pdf-color-picker-presets">
            {displayPresets.map((preset) => {
              const normalizedPreset = normalizeHex(preset, fallback);
              const isActive = normalizedPreset === safeValue;
              return (
                <button
                  key={normalizedPreset}
                  type="button"
                  className={`pdf-color-picker-preset ${isActive ? 'is-active' : ''}`}
                  style={{ '--picker-color': normalizedPreset }}
                  onClick={() => commitHex(normalizedPreset)}
                  title={normalizedPreset}
                />
              );
            })}
          </div>

          <div className="pdf-color-picker-sliders">
            <ColorRange
              label="Tono"
              value={hsl.h}
              min={0}
              max={360}
              onChange={(nextHue) => commitHsl({ h: nextHue })}
              background="linear-gradient(90deg, #FF3B30 0%, #FF9500 16%, #FFD60A 32%, #34C759 48%, #0A84FF 66%, #5E5CE6 82%, #FF2D55 100%)"
            />
            <ColorRange
              label="Saturacion"
              value={hsl.s}
              min={0}
              max={100}
              onChange={(nextSaturation) => commitHsl({ s: nextSaturation })}
              background={saturationBackground}
            />
            <ColorRange
              label="Luz"
              value={hsl.l}
              min={0}
              max={100}
              onChange={(nextLightness) => commitHsl({ l: nextLightness })}
              background={lightnessBackground}
            />
          </div>

          <div className="pdf-color-picker-rgb">
            {[
              ['R', rgb.r, 'r'],
              ['G', rgb.g, 'g'],
              ['B', rgb.b, 'b'],
            ].map(([channelLabel, channelValue, channelKey]) => (
              <label key={channelKey} className="pdf-color-picker-rgb-field">
                <span>{channelLabel}</span>
                <input
                  type="number"
                  min={0}
                  max={255}
                  className="input input-no-spinner"
                  value={channelValue}
                  onChange={(event) => {
                    const rawValue = Number(event.target.value);
                    commitRgb({ [channelKey]: Number.isFinite(rawValue) ? rawValue : 0 });
                  }}
                />
              </label>
            ))}
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
