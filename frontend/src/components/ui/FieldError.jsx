export function FieldError({ message }) {
  if (!message) return null;
  return (
    <p style={{ fontSize: '11px', color: '#DC2626', marginTop: '3px', lineHeight: 1.4 }}>
      {message}
    </p>
  );
}
