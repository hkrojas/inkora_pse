import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Crop, QrCode, RotateCcw, X, ZoomIn } from 'lucide-react';
import Spinner from '../ui/Spinner';
import {
  constrainSquareCrop,
  cropImageElementToPngFile,
  getCropPercentStyle,
  getImagePointerPosition,
  getInitialSquareCrop,
  moveSquareCropByPointer,
  resizeSquareCropFromHandle,
} from '../../lib/utils/imageCrop';

const RESIZE_HANDLES = ['nw', 'ne', 'sw', 'se'];
const BASE_PREVIEW_MAX_WIDTH = 620;
const BASE_PREVIEW_MAX_HEIGHT = 440;
const MIN_ZOOM = 1;
const MAX_ZOOM = 2.4;
const ZOOM_STEP = 0.05;

export default function PaymentQrCropper({
  file,
  open,
  uploading = false,
  onCancel,
  onConfirm,
}) {
  const imageRef = useRef(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  const [crop, setCrop] = useState({ x: 0, y: 0, size: 0 });
  const [interaction, setInteraction] = useState(null);
  const [error, setError] = useState(null);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    if (!open || !file) {
      setPreviewUrl('');
      setImageSize({ width: 0, height: 0 });
      setCrop({ x: 0, y: 0, size: 0 });
      setInteraction(null);
      setZoom(1);
      return undefined;
    }

    const nextUrl = URL.createObjectURL(file);
    setPreviewUrl(nextUrl);
    setError(null);

    return () => {
      URL.revokeObjectURL(nextUrl);
    };
  }, [file, open]);

  const cropStyle = useMemo(
    () => getCropPercentStyle(crop, imageSize),
    [crop, imageSize],
  );
  const maxSize = Math.min(imageSize.width, imageSize.height);
  const minSize = maxSize ? Math.min(maxSize, Math.max(64, Math.round(maxSize * 0.28))) : 1;
  const canEdit = Boolean(maxSize && previewUrl);

  const baseDisplayWidth = useMemo(() => {
    if (!imageSize.width || !imageSize.height) return 0;
    const widthLimit = Math.min(imageSize.width, BASE_PREVIEW_MAX_WIDTH);
    const heightLimit = Math.round(imageSize.width * (BASE_PREVIEW_MAX_HEIGHT / imageSize.height));
    return Math.max(1, Math.min(widthLimit, heightLimit));
  }, [imageSize]);

  const imageRenderStyle = baseDisplayWidth
    ? { width: `${Math.round(baseDisplayWidth * zoom)}px`, maxWidth: 'none', maxHeight: 'none' }
    : undefined;

  const getPointerPosition = useCallback((event) => {
    const rect = imageRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return getImagePointerPosition(event, rect, imageSize);
  }, [imageSize]);

  useEffect(() => {
    if (!interaction) return undefined;

    const handlePointerMove = (event) => {
      event.preventDefault();
      const nextPoint = getPointerPosition(event);
      if (interaction.type === 'resize') {
        setCrop(resizeSquareCropFromHandle(
          interaction.startCrop,
          interaction.handle,
          nextPoint,
          imageSize,
          minSize,
        ));
        return;
      }
      setCrop(moveSquareCropByPointer(
        interaction.startCrop,
        interaction.startPoint,
        nextPoint,
        imageSize,
      ));
    };

    const handlePointerEnd = () => setInteraction(null);

    window.addEventListener('pointermove', handlePointerMove, { passive: false });
    window.addEventListener('pointerup', handlePointerEnd);
    window.addEventListener('pointercancel', handlePointerEnd);
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerEnd);
      window.removeEventListener('pointercancel', handlePointerEnd);
    };
  }, [getPointerPosition, interaction, imageSize, minSize]);

  if (!open) return null;

  const startCropInteraction = (event, type, handle = null) => {
    if (!canEdit || uploading) return;
    event.preventDefault();
    setError(null);
    setInteraction({
      type,
      handle,
      startCrop: crop,
      startPoint: getPointerPosition(event),
    });
  };

  const handleImageLoad = (event) => {
    const width = event.currentTarget.naturalWidth;
    const height = event.currentTarget.naturalHeight;
    const nextSize = { width, height };
    setImageSize(nextSize);
    setCrop(getInitialSquareCrop(width, height));
    setInteraction(null);
    setZoom(1);
  };

  const resetCrop = () => {
    setCrop(getInitialSquareCrop(imageSize.width, imageSize.height));
    setError(null);
  };

  const useFullImage = () => {
    const size = Math.min(imageSize.width, imageSize.height);
    setCrop(constrainSquareCrop({
      x: Math.round((imageSize.width - size) / 2),
      y: Math.round((imageSize.height - size) / 2),
      size,
    }, imageSize));
    setError(null);
  };

  const handleConfirm = async () => {
    if (!imageRef.current || !file) return;
    setError(null);
    try {
      const croppedFile = await cropImageElementToPngFile(imageRef.current, crop, file.name);
      await onConfirm(croppedFile);
    } catch (err) {
      setError(err?.message || 'No se pudo preparar el recorte del QR.');
    }
  };

  const modal = (
    <div className="settings-qr-crop-overlay" role="dialog" aria-modal="true" aria-label="Recortar QR de cobro">
      <div className="settings-qr-crop-panel">
        <div className="settings-qr-crop-header">
          <div className="settings-qr-crop-icon">
            <QrCode size={18} />
          </div>
          <div>
            <h3>Recortar QR de cobro</h3>
            <p>Arrastra el cuadro sobre el QR y ajusta sus esquinas antes de guardarlo.</p>
          </div>
          <button type="button" className="settings-qr-crop-close" onClick={onCancel} disabled={uploading}>
            <X size={18} />
          </button>
        </div>

        <div className="settings-qr-crop-body">
          <div className="settings-qr-crop-stage">
            <div className="settings-qr-crop-stage-inner">
              {previewUrl ? (
                <div className="settings-qr-crop-image-wrap">
                  <img
                    ref={imageRef}
                    src={previewUrl}
                    alt="Captura de QR para recortar"
                    style={imageRenderStyle}
                    onLoad={handleImageLoad}
                  />
                  {canEdit && (
                    <div
                      className={`settings-qr-crop-box${interaction ? ' is-active' : ''}`}
                      style={cropStyle}
                      role="button"
                      tabIndex={0}
                      aria-label="Mover area de recorte del QR"
                      onPointerDown={(event) => startCropInteraction(event, 'move')}
                    >
                      <span className="settings-qr-crop-guides" />
                      {RESIZE_HANDLES.map((handle) => (
                        <span
                          key={handle}
                          className={`settings-qr-crop-handle settings-qr-crop-handle--${handle}`}
                          aria-hidden="true"
                          onPointerDown={(event) => {
                            event.stopPropagation();
                            startCropInteraction(event, 'resize', handle);
                          }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="settings-qr-crop-empty">
                  <QrCode size={34} />
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="settings-qr-crop-footer">
          <div className="settings-qr-crop-toolbar">
            <label className="settings-qr-crop-zoom-control">
              <span>
                <ZoomIn size={15} /> Zoom <strong>{Math.round(zoom * 100)}%</strong>
              </span>
              <input
                type="range"
                min={MIN_ZOOM}
                max={MAX_ZOOM}
                step={ZOOM_STEP}
                value={zoom}
                disabled={!canEdit || uploading}
                onChange={(event) => setZoom(Number(event.target.value))}
              />
            </label>
            <div className="settings-qr-crop-toolrow">
              <button type="button" className="btn-secondary" onClick={resetCrop} disabled={!canEdit || uploading}>
                <RotateCcw size={15} /> Centrar
              </button>
              <button type="button" className="btn-secondary" onClick={useFullImage} disabled={!canEdit || uploading}>
                <Crop size={15} /> Completo
              </button>
            </div>
          </div>

          {error && <p className="settings-qr-crop-error">{error}</p>}

          <div className="settings-qr-crop-actions">
            <button type="button" className="btn-secondary" onClick={onCancel} disabled={uploading}>
              Cancelar
            </button>
            <button type="button" className="btn-primary" onClick={handleConfirm} disabled={!canEdit || uploading}>
              {uploading ? (
                <>
                  <Spinner size="sm" /> Guardando...
                </>
              ) : (
                <>
                  <Crop size={16} /> Guardar QR limpio
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}
