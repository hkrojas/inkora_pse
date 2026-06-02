import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Crop, QrCode, RotateCcw, X } from 'lucide-react';
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

  useEffect(() => {
    if (!open || !file) {
      setPreviewUrl('');
      setImageSize({ width: 0, height: 0 });
      setCrop({ x: 0, y: 0, size: 0 });
      setInteraction(null);
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
  const maxX = Math.max(0, imageSize.width - crop.size);
  const maxY = Math.max(0, imageSize.height - crop.size);
  const canEdit = Boolean(maxSize && previewUrl);

  const updateCrop = (partial) => {
    setCrop((current) => constrainSquareCrop({ ...current, ...partial }, imageSize));
  };

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

  return (
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
            {previewUrl ? (
              <div className="settings-qr-crop-image-wrap">
                <img ref={imageRef} src={previewUrl} alt="Captura de QR para recortar" onLoad={handleImageLoad} />
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

          <aside className="settings-qr-crop-controls">
            <div>
              <span className="settings-qr-crop-kicker">Vista final</span>
              <strong>Solo el cuadro seleccionado se guardara</strong>
              <p>Mueve el cuadro con el mouse y cambia su tamano desde las esquinas. Los controles son ajuste fino.</p>
            </div>

            <label>
              <span>Tamano del recorte</span>
              <input
                type="range"
                min={minSize}
                max={maxSize || 1}
                value={crop.size || minSize}
                disabled={!canEdit || uploading}
                onChange={(event) => updateCrop({ size: Number(event.target.value) })}
              />
            </label>

            <label>
              <span>Posicion horizontal</span>
              <input
                type="range"
                min="0"
                max={maxX || 0}
                value={crop.x || 0}
                disabled={!canEdit || uploading}
                onChange={(event) => updateCrop({ x: Number(event.target.value) })}
              />
            </label>

            <label>
              <span>Posicion vertical</span>
              <input
                type="range"
                min="0"
                max={maxY || 0}
                value={crop.y || 0}
                disabled={!canEdit || uploading}
                onChange={(event) => updateCrop({ y: Number(event.target.value) })}
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

            {error && <p className="settings-qr-crop-error">{error}</p>}
          </aside>
        </div>

        <div className="settings-qr-crop-footer">
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
  );
}
