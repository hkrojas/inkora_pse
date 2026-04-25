export function FieldError({ message }) {
  if (!message) return null;
  return (
    <p style={{ fontSize: '11px', color: 'var(--color-error)', marginTop: '3px', lineHeight: 1.4 }}>
      {message}
    </p>
  );
}
