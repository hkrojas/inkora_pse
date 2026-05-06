import { useMemo } from 'react';

function getInitials(name) {
  if (!name) return '?';
  const words = name.trim().split(/\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

const GRADIENTS = [
  'linear-gradient(135deg, #E8F5D0, #D6EDBE)',
  'linear-gradient(135deg, #dcfce7, #bbf7d0)',
  'linear-gradient(135deg, #fef3c7, #fde68a)',
  'linear-gradient(135deg, #ede9fe, #ddd6fe)',
  'linear-gradient(135deg, #fee2e2, #fecaca)',
];

function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash);
}

export default function TableAvatar({ name, size = 32, className = '' }) {
  const initials = useMemo(() => getInitials(name), [name]);
  const gradient = useMemo(() => {
    const idx = hashString(name || '?') % GRADIENTS.length;
    return GRADIENTS[idx];
  }, [name]);

  return (
    <span
      className={`ink-table-avatar ${className}`.trim()}
      style={{
        width: size,
        height: size,
        background: gradient,
        fontSize: size < 28 ? 10 : 12,
      }}
      aria-hidden="true"
    >
      {initials}
    </span>
  );
}
